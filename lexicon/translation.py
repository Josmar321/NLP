"""Traducción composicional: reglas explícitas y léxico inducido solo de train."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

from lexicon.preprocessing import ROOT, prepare, preprocess_row, tokenize, normalize_text, normalize_exact_match
from lexicon.eda import induce_categories, parse_source, bilingual_parts
from lexicon.experimental import load_event, inspect_event


class UnsupportedSentence(ValueError):
    """La entrada no está cubierta por el vocabulario o la gramática observados."""


class JaccardTranslator:
    def fit(self, rows):
        if not rows:
            raise ValueError('Entrenamiento vacío')
        self.rows = list(rows)
        self.token_sets = [set(tokenize(r['naviri'])) for r in rows]
        return self

    def translate(self, sentence):
        query = set(tokenize(sentence))
        scores = [len(query & words) / len(query | words) if query | words else 0.0 for words in self.token_sets]
        # Igual que la plantilla: los empates se resuelven por orden de train.
        index = max(range(len(scores)), key=scores.__getitem__)
        return self.rows[index]['espanol']


class CompositionalTranslator:
    def fit(self, rows):
        if not rows:
            raise ValueError('Entrenamiento vacío')
        rows = [preprocess_row(row) for row in rows]
        self.maps, self.morphology, self.evidence = induce_categories(rows)
        if self.evidence['rejected_train_ids'] or self.evidence['negation_disagreement_ids']:
            raise ValueError('Entrenamiento incompatible con la hipótesis gramatical; revisar evidencia')
        for category, words in self.maps.items():
            if any(len(targets) != 1 for targets in words.values()):
                raise ValueError(f'Correspondencias ambiguas en {category}; no se elige una silenciosamente')
        self.lexicon = {category: {word: targets.most_common(1)[0][0] for word, targets in words.items()} for category, words in self.maps.items()}
        self.fit_rows = len(rows)
        if any(self.analyze(row['naviri']) is None for row in rows):
            raise ValueError('La hipótesis de orden no cubre todas las fuentes de entrenamiento')
        return self

    def analyze(self, sentence):
        return parse_source(tokenize(sentence), self.maps, self.morphology)

    def translate(self, sentence, *, use_tense=True, use_negation=True, reorder=True):
        parts = self.analyze(sentence)
        if parts is None:
            raise UnsupportedSentence('Vocabulario o estructura fuera de la cobertura de entrenamiento')
        word = tokenize(sentence)[-1]
        verb_form = word if use_tense else parts['root']
        if verb_form not in self.lexicon['verb']:
            raise UnsupportedSentence('No se observó la conjugación española de esta raíz')
        subject = self.lexicon['subject'][parts['subject']]
        obj = self.lexicon['object'][parts['object']]
        verb = self.lexicon['verb'][verb_form]
        negation = ['no'] if parts['negative'] and use_negation else []
        location = ['en ' + self.lexicon['location'][parts['location']]] if parts['location'] != '∅' else []
        segments = [subject, *negation, verb, obj, *location] if reorder else [subject, obj, *location, *negation, verb]
        return ' '.join(segments) + '.'

    def save(self, path):
        state = {'format_version': 1, 'fit_split': 'train_parallel.csv', 'fit_rows': self.fit_rows,
                 'grammar': 'S O [L] [nu] V -> S [no] V O [en L]',
                 'maps': {cat: {word: dict(counts) for word, counts in words.items()} for cat, words in self.maps.items()},
                 'morphology': self.morphology, 'evidence': self.evidence}
        Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    @classmethod
    def load(cls, path):
        state = json.loads(Path(path).read_text(encoding='utf-8'))
        if state['format_version'] != 1:
            raise ValueError('Versión de traductor no compatible')
        model = cls()
        model.fit_rows, model.evidence = state['fit_rows'], state['evidence']
        model.maps = {cat: {word: Counter(counts) for word, counts in words.items()} for cat, words in state['maps'].items()}
        if set(model.maps) != {'subject', 'object', 'verb', 'location'} or any(len(targets) != 1 for words in model.maps.values() for targets in words.values()):
            raise ValueError('Léxico del traductor no válido')
        model.lexicon = {cat: {word: next(iter(counts)) for word, counts in words.items()} for cat, words in model.maps.items()}
        model.morphology = {word: tuple(value) for word, value in state['morphology'].items()}
        return model


class ConversationRouter:
    """Memoria explícita de expresiones oficiales; no generalización conversacional."""
    def __init__(self, translator, phrases):
        self.translator = translator
        self.phrases = {}
        for row in phrases:
            key = normalize_text(row['naviri'])  # Conserva ? y no equipara seni? con seni.
            if key in self.phrases and self.phrases[key] != row['espanol']:
                raise ValueError('Expresiones oficiales con traducciones contradictorias')
            self.phrases[key] = row['espanol']

    def translate(self, sentence):
        key = normalize_text(sentence)
        if key in self.phrases:
            return {'prediction': self.phrases[key], 'route': 'official_phrase_memory'}
        return {'prediction': self.translator.translate(sentence), 'route': 'compositional'}


def classify_error(reference, prediction, rules):
    ref = bilingual_parts({'espanol': reference})
    pred = bilingual_parts({'espanol': prediction})
    if ref is None or pred is None:
        return ['estructura_o_abstencion']
    rs, rn, rv, ro, rl = ref.groups()
    ps, pn, pv, po, pl = pred.groups()
    errors = [name for name, a, b in [('sujeto', rs, ps), ('objeto', ro, po), ('lugar', rl, pl), ('negacion', bool(rn), bool(pn))] if a != b]
    inverse = {target: rules.morphology[word] for word, target in rules.lexicon['verb'].items()}
    if rv != pv:
        if rv in inverse and pv in inverse:
            if inverse[rv][0] != inverse[pv][0]:
                errors.append('accion')
            if inverse[rv][1] != inverse[pv][1]:
                errors.append('tiempo')
        else:
            errors.append('verbo_no_identificado')
    return errors or ['otra_diferencia_superficial']


def score_predictions(references, predictions):
    # Se usa la implementación oficial de sacrebleu, sin reemplazarla por una aproximación.
    import sacrebleu
    from sacrebleu.metrics import CHRF
    if not references or len(references) != len(predictions):
        raise ValueError('Referencias y predicciones deben tener igual longitud no vacía')
    refs = [normalize_exact_match(s) for s in references]
    preds = [normalize_exact_match(s) for s in predictions]
    metric = CHRF(char_order=6, word_order=0, beta=2, lowercase=False, whitespace=False, eps_smoothing=False)
    score = metric.corpus_score(preds, [refs])
    exact = sum(a == b for a, b in zip(refs, preds))
    return {'n': len(refs), 'correct': exact, 'exact_match': exact / len(refs), 'chrf': score.score,
            'chrf_signature': str(metric.get_signature()), 'sacrebleu': sacrebleu.__version__}


def validation_groups(rows, training, rules):
    train_triples = {(p['subject'], p['object'], p['root']) for r in training if (p := rules.analyze(r['naviri']))}
    groups = {name: [] for name in ['all', 'negation', 'past', 'future', 'present', 'location', 'without_location', 'novel_triple', 'seen_triple', 'unparsed']}
    for i, row in enumerate(rows):
        groups['all'].append(i)
        p = rules.analyze(row['naviri'])
        if p is None:
            groups['unparsed'].append(i)
            continue
        groups[{'pasado': 'past', 'presente': 'present', 'futuro': 'future'}[p['tense']]].append(i)
        if p['negative']:
            groups['negation'].append(i)
        groups['location' if p['location'] != '∅' else 'without_location'].append(i)
        triple = p['subject'], p['object'], p['root']
        groups['novel_triple' if triple not in train_triples else 'seen_triple'].append(i)
    return groups


def translate_rows(rows, translator):
    predictions, abstentions = [], []
    for row in rows:
        try:
            predictions.append(translator(row['naviri']))
        except UnsupportedSentence:
            predictions.append('')
            abstentions.append(row['id'])
    return predictions, abstentions


def write_predictions(path, rows, predictions, expected_rows=40):
    if len(rows) != expected_rows or len(predictions) != expected_rows or len({r['id'] for r in rows}) != expected_rows or any(not p.strip() for p in predictions):
        raise ValueError('Predicciones incompletas, vacías o con IDs repetidos')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['id', 'prediccion'])
        writer.writeheader()
        writer.writerows({'id': row['id'], 'prediccion': p} for row, p in zip(rows, predictions))
    with path.open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        written = list(reader)
        if reader.fieldnames != ['id', 'prediccion'] or [r['id'] for r in written] != [r['id'] for r in rows]:
            raise ValueError('El CSV exportado no conserva columnas u orden')


def export_translation(root=ROOT):
    root = Path(root)
    data, _ = prepare(root)
    event = load_event(root)
    rules = CompositionalTranslator().fit(data['train'])
    baseline = JaccardTranslator().fit(data['train'])
    systems = {
        'jaccard': baseline.translate,
        'compositional': rules.translate,
        'without_tense': lambda s: rules.translate(s, use_tense=False),
        'without_negation': lambda s: rules.translate(s, use_negation=False),
        'without_reordering': lambda s: rules.translate(s, reorder=False),
    }
    groups = validation_groups(data['validation'], data['train'], rules)
    references = [r['espanol'] for r in data['validation']]
    results, details, errors = {}, [], []
    for name, translator in systems.items():
        predictions, abstentions = translate_rows(data['validation'], translator)
        results[name] = {'abstention_ids': abstentions, 'groups': {}}
        for group, indices in groups.items():
            results[name]['groups'][group] = score_predictions([references[i] for i in indices], [predictions[i] for i in indices]) if indices else {'n': 0, 'correct': 0, 'exact_match': None, 'chrf': None}
        for i, row in enumerate(data['validation']):
            correct = normalize_exact_match(references[i]) == normalize_exact_match(predictions[i])
            record = {'system': name, 'id': row['id'], 'naviri': row['naviri'], 'reference': references[i], 'prediction': predictions[i], 'correct': correct}
            details.append(record)
            if not correct:
                errors.append({**record, 'error_types': classify_error(references[i], predictions[i], rules)})
    destination = root / 'resultados' / 'traduccion_04'
    destination.mkdir(parents=True, exist_ok=True)
    rules.save(destination / 'traductor_composicional.json')
    for name, records in [('validacion_detalle.csv', details), ('errores.csv', errors)]:
        with (destination / name).open('w', encoding='utf-8', newline='') as handle:
            fields = list(records[0]) if records else ['system', 'id', 'naviri', 'reference', 'prediction', 'correct', 'error_types']
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
    output_metrics = []
    for name, result in results.items():
        for group, values in result['groups'].items():
            output_metrics.append({'system': name, 'group': group, **values})
    with (destination / 'metricas_grupos.csv').open('w', encoding='utf-8', newline='') as handle:
        fields = ['system', 'group', 'n', 'correct', 'exact_match', 'chrf', 'chrf_signature', 'sacrebleu']
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_metrics)
    export_summary = {}
    for split, rows, filename in [('public', data['public'], 'predicciones.csv'), ('phase5', event['phase5'], 'predicciones_fase5.csv')]:
        predictions, abstentions = translate_rows(rows, rules.translate)
        if abstentions:
            raise ValueError(f'{split}: mensajes sin cobertura; no se genera una entrega incompleta: {abstentions}')
        write_predictions(root / filename, rows, predictions)
        # Copia junto al experimento para conservar su procedencia.
        write_predictions(destination / filename, rows, predictions)
        trace = [{'id': row['id'], 'naviri': row['naviri'], 'prediccion': prediction, **rules.analyze(row['naviri'])} for row, prediction in zip(rows, predictions)]
        with (destination / f'trazas_{split}.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trace[0]))
            writer.writeheader()
            writer.writerows(trace)
        export_summary[split] = {'rows': len(rows), 'filename': filename, 'reference_available': False}
    router = ConversationRouter(rules, event['conversation'])
    known_phrases = [{'naviri': row['naviri'], **router.translate(row['naviri'])} for row in event['conversation']]
    report = {
        'python': platform.python_version(), 'fit_split': 'train_parallel.csv', 'fit_rows': len(data['train']),
        'grammar': 'S O [L] [nu] V -> S [no] V O [en L]',
        'lexicon_sizes': {cat: len(words) for cat, words in rules.lexicon.items()},
        'training_evidence': rules.evidence,
        'hints_audit': inspect_event(data, event),
        'hints_used_to_fit': False, 'conversation_used_to_fit_rules': False,
        'monolingual_used_to_fit_rules': False, 'lm_used_to_rerank': False,
        'metric_preprocessing': 'EM y chrF sobre NFC, minúsculas, espacios normalizados y sin puntuación final; puntuación interna conservada.',
        'chrf_scale': '0..100; CHRF char_order=6, word_order=0, beta=2; espacios excluidos',
        'validation_results': results, 'exports': export_summary,
        'conversation_known_phrases': known_phrases,
        'data_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'datos').rglob('*.csv'))},
        'policy': 'Gramática explícita respaldada por train; léxico inducido. Sin correcciones de validación ni selección por test oculto. Cada ablación cambia un único componente de generación.',
    }
    (destination / 'metricas.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    report = export_translation()
    for name, result in report['validation_results'].items():
        print(name, result['groups']['all'])
