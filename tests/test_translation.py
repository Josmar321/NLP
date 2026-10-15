import csv
import tempfile
import unittest
import importlib.util
from pathlib import Path
from lexicon.preprocessing import prepare, normalize_exact_match
from lexicon.translation import (
    CompositionalTranslator, JaccardTranslator, ConversationRouter,
    UnsupportedSentence, classify_error, validation_groups, write_predictions,
    score_predictions,
)


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.data, _ = prepare()
        self.rules = CompositionalTranslator().fit(self.data['train'])

    def test_novel_composition_and_temporal_ablation(self):
        # Composición de elementos conocidos, sin memorizar una referencia de validación.
        source = 'vonu zura miri nu lomuta.'
        self.assertEqual(self.rules.translate(source), 'el viajero no buscó la llave en el bosque.')
        self.assertEqual(self.rules.translate(source, use_tense=False), 'el viajero no busca la llave en el bosque.')
        self.assertEqual(self.rules.translate(source, use_negation=False), 'el viajero buscó la llave en el bosque.')
        self.assertEqual(self.rules.morphology['kori'], ('kori', 'presente'))
        self.assertEqual(self.rules.morphology['koriri'], ('kori', 'futuro'))

    def test_unsupported_inputs_do_not_silently_retrieve(self):
        for source in ['vonu desconocido lomu.', 'vonu zura nu miri lomu.', 'vonu zura lomux.', '']:
            with self.assertRaises(UnsupportedSentence):
                self.rules.translate(source)

    def test_lexical_conflict_fails_training(self):
        bad = dict(self.data['train'][0])
        bad['espanol'] = bad['espanol'].replace('el viajero', 'el maestro')
        with self.assertRaises(ValueError):
            CompositionalTranslator().fit(self.data['train'] + [bad])

    def test_phrase_memory_keeps_questions_distinct(self):
        router = ConversationRouter(self.rules, [{'naviri': 'seni?', 'espanol': '¿Cómo estás?'}])
        self.assertEqual(router.translate('SENI?')['route'], 'official_phrase_memory')
        with self.assertRaises(UnsupportedSentence):
            router.translate('seni')

    def test_group_accounting_and_baseline_tie(self):
        groups = validation_groups(self.data['validation'], self.data['train'], self.rules)
        self.assertEqual(len(groups['novel_triple']), 87)
        self.assertEqual(len(groups['future']), 22)
        self.assertEqual(len(groups['past']) + len(groups['present']) + len(groups['future']), 120)
        baseline = JaccardTranslator().fit(self.data['train'][:2])
        self.assertEqual(baseline.translate('desconocido'), self.data['train'][0]['espanol'])

    def test_model_roundtrip_and_csv_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rules.json'
            self.rules.save(path)
            loaded = CompositionalTranslator.load(path)
            for row in self.data['public']:
                self.assertEqual(loaded.translate(row['naviri']), self.rules.translate(row['naviri']))
            target = Path(directory) / 'predicciones.csv'
            rows = self.data['public']
            predictions = [loaded.translate(r['naviri']) for r in rows]
            write_predictions(target, rows, predictions)
            with target.open(encoding='utf-8', newline='') as f:
                exported = list(csv.DictReader(f))
            self.assertEqual([r['id'] for r in exported], [r['id'] for r in rows])
            with self.assertRaises(ValueError):
                write_predictions(target, rows, [''] * 40)

    def test_negation_is_a_semantic_error_even_with_similar_characters(self):
        errors = classify_error('el viajero no busca la llave.', 'el viajero busca la llave.', self.rules)
        self.assertEqual(errors, ['negacion'])

    @unittest.skipUnless(importlib.util.find_spec('sacrebleu'), 'Instalar requirements-traduccion.txt para probar chrF')
    def test_official_chrf_and_normalization(self):
        perfect = score_predictions(['EL NIÑO busca.'], ['el niño busca'])
        self.assertEqual(perfect['exact_match'], 1)
        self.assertAlmostEqual(perfect['chrf'], 100)
        different = score_predictions(['el niño no busca.'], ['el niño busca.'])
        self.assertEqual(different['exact_match'], 0)
        self.assertGreater(different['chrf'], 0)
        self.assertLess(different['chrf'], 100)


if __name__ == '__main__':
    unittest.main()
