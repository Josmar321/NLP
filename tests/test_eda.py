import unittest
from lexicon.eda import analyze, induce_categories, ngrams, parse_source, js_divergence
from lexicon.preprocessing import prepare


class EdaTests(unittest.TestCase):
    def test_morphology_does_not_confuse_root_with_suffix(self):
        data, _ = prepare()
        maps, morphology, _ = induce_categories(data['train'])
        self.assertEqual(morphology['kori'], ('kori', 'presente'))
        self.assertEqual(morphology['koriri'], ('kori', 'futuro'))
        self.assertEqual(morphology['korita'], ('kori', 'pasado'))
        self.assertIsNone(parse_source(['vonu', 'zura', 'desconocido', 'kori'], maps, morphology))
        self.assertIsNone(parse_source(['vonu', 'zura', 'nu', 'miri', 'kori'], maps, morphology))

    def test_ngram_boundaries_and_divergence(self):
        self.assertEqual(ngrams(['a', 'b'], 3), [('<s>', '<s>', 'a'), ('<s>', 'a', 'b'), ('a', 'b', '</s>')])
        self.assertAlmostEqual(js_divergence({'a': 2}, {'a': 8}), 0)
        self.assertAlmostEqual(js_divergence({'a': 2}, {'b': 8}), 1)

    def test_accounting_and_frozen_training_categories(self):
        data, counts, parsed, metrics = analyze()
        self.assertEqual(metrics['training_evidence']['rejected_train_ids'], [])
        self.assertFalse(any(r['conflict'] for r in metrics['lexicon']))
        self.assertEqual(metrics['splits']['validation']['phenomena']['futuro'], 22)
        self.assertEqual(metrics['monolingual_without_public']['removed'], 28)
        for split, rows in data.items():
            info = metrics['splits'][split]
            self.assertEqual(info['parsed'], len(rows))
            self.assertEqual(sum(info['signatures'].values()), len(rows))
            self.assertEqual(sum(counts[split].values()), info['tokens'])
        self.assertEqual(metrics['splits']['validation']['novel_pairs']['subject__object']['unseen_rows'], 4)


if __name__ == '__main__':
    unittest.main()
