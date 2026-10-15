"""Experimentos 03: auditoría de fase 5 y modelos de lenguaje estadísticos."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import random
from collections import Counter
from pathlib import Path

from lexicon.preprocessing import ROOT, prepare, normalize_text, normalize_exact_match, tokenize
from lexicon.eda import induce_categories, parse_source
from lexicon.ngram import NGramLM

SEED = 20261014
EVENT_FILES = {
    'conversation': ('LEXICON_X_Comunicacion_Inicial_Noelia.csv', ['naviri', 'espanol', 'categoria']),
    'phase5': ('LEXICON_X_Fase5_Nuevos_Mensajes.csv', ['id', 'naviri']),
    'hints': ('LEXICON_X_Pistas_Lexicas_Estudiantes.csv', ['naviri', 'espanol', 'categoria', 'observacion']),
}


def load_event(root=ROOT):
    event = {}
    for kind, (filename, columns) in EVENT_FILES.items():
        path = Path(root) / 'datos' / 'evento_fase_5' / filename
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns:
                raise ValueError(f'{path}: columnas inesperadas {reader.fieldnames}')
            rows = list(reader)
        if not rows:
            raise ValueError(f'{path}: archivo vacío')
        for row in rows:
            if set(row) != set(columns) or any(not isinstance(row[k], str) or not row[k].strip() for k in columns):
                raise ValueError(f'{path}: fila incompleta o mal formada')
        if kind == 'phase5' and len({r['id'] for r in rows}) != len(rows):
            raise ValueError('Fase 5 tiene IDs repetidos')
        # Las pistas conservan su guion inicial: -ta no es una palabra ta.
        event[kind] = rows
    return event


def inspect_event(data, event):
    maps, morphology, evidence = induce_categories(data['train'])
    vocab = {w for r in data['train'] for w in r['naviri_tokens']}
    sources = {s: {normalize_exact_match(r['naviri']) for r in rows} for s, rows in data.items()}
    phase_sources = {normalize_exact_match(r['naviri']) for r in event['phase5']}
    hint_checks = []
    categories = {'sujeto': 'subject', 'objeto': 'object', 'lugar': 'location', 'verbo (presente)': 'verb'}
    for row in event['hints']:
        word, target = normalize_text(row['naviri']), normalize_text(row['espanol'])
        category = categories.get(row['categoria'])
        if category:
            # Las pistas incluyen en; el lexicón de lugares guarda solo el sintagma nominal.
            expected = target[3:] if category == 'location' and target.startswith('en ') else target
            candidates = maps[category].get(word, {})
            support = sum(candidates.values())
            ok = expected in candidates and len(candidates) == 1
        elif word == 'nu':
            support = sum('nu' in r['naviri_tokens'] for r in data['train'])
            ok = target == 'no' and not evidence['negation_disagreement_ids']
        else:
            tense = {'-ta': 'pasado', '-ri': 'futuro'}.get(word)
            support = sum(maps['verb'][form].total() for form, (_, t) in morphology.items() if t == tense)
            ok = tense is not None and target == tense and support > 0
        hint_checks.append({**row, 'consistent_with_train': ok, 'train_support': support})
    greeting_vocab = {w for r in event['conversation'] for w in tokenize(r['naviri'])}
    phase_parsed = [parse_source(tokenize(r['naviri']), maps, morphology) for r in event['phase5']]
    # Si surgieran claves conversacionales contradictorias, se informan, no se elige una silenciosamente.
    phrase_targets = {}
    for row in event['conversation']:
        phrase_targets.setdefault(normalize_text(row['naviri']), set()).add(row['espanol'])
    return {
        'rows': {key: len(rows) for key, rows in event.items()},
        'hint_checks': hint_checks,
        'hints_consistent': sum(r['consistent_with_train'] for r in hint_checks),
        'phase5_source_overlaps': {s: len(phase_sources & ss) for s, ss in sources.items()},
        'phase5_oov_types': sorted({w for r in event['phase5'] for w in tokenize(r['naviri'])} - vocab),
        'phase5_parsed': sum(parse_source(tokenize(r['naviri']), maps, morphology) is not None for r in event['phase5']),
        'phase5_phenomena': {
            'negative': sum(p['negative'] for p in phase_parsed if p),
            'past': sum(p['tense'] == 'pasado' for p in phase_parsed if p),
            'future': sum(p['tense'] == 'futuro' for p in phase_parsed if p),
            'location': sum(p['location'] != '∅' for p in phase_parsed if p),
        },
        'conversation_new_types': sorted(greeting_vocab - vocab),
        'conversation_categories': dict(Counter(r['categoria'] for r in event['conversation'])),
        'conversation_conflicting_phrases': {k: sorted(v) for k, v in phrase_targets.items() if len(v) > 1},
        'training_evidence': evidence,
    }


def partition_monolingual(data, event, seed=SEED):
    forbidden = {normalize_exact_match(r['naviri']) for r in data['public'] + event['phase5']}
    clean, exposed = [], []
    for row in data['monolingual']:
        (exposed if normalize_exact_match(row['naviri']) in forbidden else clean).append(row)
    shuffled = list(clean)
    random.Random(seed).shuffle(shuffled)
    n_train, n_dev = int(.8 * len(shuffled)), int(.1 * len(shuffled))
    splits = {'train': shuffled[:n_train], 'dev': shuffled[n_train:n_train + n_dev], 'test': shuffled[n_train + n_dev:]}
    sets = {k: {normalize_exact_match(r['naviri']) for r in rows} for k, rows in splits.items()}
    if any(sets[a] & sets[b] for a, b in [('train', 'dev'), ('train', 'test'), ('dev', 'test')]):
        raise ValueError('Fuentes idénticas entre particiones del LM')
    return splits, exposed


def tokens_of(rows):
    return [r.get('naviri_tokens') or tokenize(r['naviri']) for r in rows]


def model_specs():
    for order in [1, 2, 3]:
        for alpha in [.01, .05, .1, .5, 1.0]:
            yield {'family': ['unigram', 'bigram', 'trigram'][order - 1], 'order': order, 'alpha': alpha, 'weights': None}
    for alpha in [.01, .05, .1, .5, 1.0]:
        for weights in [(.1, .3, .6), (.1, .6, .3), (.2, .4, .4)]:
            yield {'family': 'interpolated', 'order': 3, 'alpha': alpha, 'weights': weights}


def instantiate(spec, train_tokens, vocabulary):
    return NGramLM(spec['order'], spec['alpha'], spec['weights']).fit(train_tokens, vocabulary)


def run_experiments(root=ROOT):
    root = Path(root)
    data, _ = prepare(root)
    event = load_event(root)
    event_audit = inspect_event(data, event)
    splits, exposed = partition_monolingual(data, event)
    mono_train, dev_tokens, test_tokens = (tokens_of(splits[k]) for k in ['train', 'dev', 'test'])
    vocabulary = {w for sent in mono_train for w in sent}
    parallel_tokens = tokens_of(data['train'])
    # Todos los corpus comparados tienen exactamente el mismo inventario observado.
    # El vocabulario se fija solo con el entrenamiento del LM, no con dev/test.
    if {w for sent in parallel_tokens for w in sent} != vocabulary:
        raise ValueError('El control de vocabulario entre corpus cambió; revisar el diseño experimental')
    conditions = {
        'train_420': parallel_tokens,
        'mono_clean': mono_train,
        'train_plus_mono': parallel_tokens + mono_train,
        'mono_transductive': mono_train + tokens_of(exposed),
        'mono_sample_420': random.Random(SEED + 1).sample(mono_train, len(parallel_tokens)),
    }
    search, selected, fitted = [], [], {}
    for condition, training in conditions.items():
        family_candidates = {}
        for spec in model_specs():
            lm = instantiate(spec, training, vocabulary)
            score = lm.evaluate(dev_tokens)
            record = {'condition': condition, **spec, 'train_sentences': len(training), 'dev_perplexity': score['perplexity'], 'dev_cross_entropy_bits': score['cross_entropy_bits']}
            search.append(record)
            family_candidates.setdefault(spec['family'], []).append(record)
        for family, candidates in family_candidates.items():
            # Selección solo con desarrollo. El orden de enumeración resuelve empates.
            winner = min(candidates, key=lambda r: r['dev_perplexity'])
            lm = instantiate(winner, training, vocabulary)
            key = f'{condition}__{family}'
            fitted[key] = lm
            selected.append({**winner, 'model_key': key, 'test': lm.evaluate(test_tokens)})
    primary = min((r for r in selected if r['condition'] == 'mono_clean'), key=lambda r: r['dev_perplexity'])
    primary_lm = fitted[primary['model_key']]
    fixed_ablation = []
    for condition, training in conditions.items():
        controlled_lm = NGramLM(2, .01).fit(training, vocabulary)
        fixed_ablation.append({'condition': condition, 'order': 2, 'alpha': .01,
                               'train_sentences': len(training),
                               'dev_perplexity': controlled_lm.evaluate(dev_tokens)['perplexity'],
                               'test_perplexity': controlled_lm.evaluate(test_tokens)['perplexity']})
    external = {}
    for split, rows in [('validation_source', data['validation']), ('public_source', data['public']), ('phase5_source', event['phase5']), ('conversation_shift', event['conversation'])]:
        external[split] = primary_lm.evaluate(tokens_of(rows))
    report = {
        'seed': SEED, 'python': platform.python_version(), 'event_audit': event_audit,
        'lm_split_sizes': {k: len(v) for k, v in splits.items()},
        'excluded_target_sources': len(exposed),
        'vocabulary_fit': 'mono_clean/train', 'lexical_vocabulary_size': len(vocabulary),
        'prediction_vocabulary_size': len(vocabulary) + 2,
        'vocabulary': sorted(vocabulary), 'eos_scored': True, 'bos_scored': False,
        'unk_policy': 'Vocabulario solo de train del LM; OOV se mapea a <unk>; add-alpha reserva masa incluso sin OOV en train.',
        'candidate_count': len(search), 'selected': selected,
        'primary_model': primary, 'external_diagnostics': external,
        'fixed_bigram_ablation': fixed_ablation,
        'selection_policy': 'Mejor familia y parámetros por perplejidad de dev en mono_clean. Test no selecciona. No se reajusta con dev antes del test.',
        'data_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'datos').rglob('*.csv'))},
    }
    return report, search, splits, event, primary_lm


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def export_experiments(root=ROOT):
    report, search, splits, event, lm = run_experiments(root)
    destination = Path(root) / 'resultados' / 'experimental_03'
    destination.mkdir(parents=True, exist_ok=True)
    lm.save(destination / 'modelo_principal.json')
    (destination / 'metricas.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_csv(destination / 'busqueda_dev.csv', search, list(search[0]))
    selected_rows = [{k: v for k, v in row.items() if k != 'test'} | {'test_perplexity': row['test']['perplexity'], 'test_oov_rate': row['test']['oov_rate']} for row in report['selected']]
    write_csv(destination / 'modelos_seleccionados.csv', selected_rows, list(selected_rows[0]))
    write_csv(destination / 'ablacion_bigram_fijo.csv', report['fixed_bigram_ablation'], list(report['fixed_bigram_ablation'][0]))
    write_csv(destination / 'contraste_pistas.csv', report['event_audit']['hint_checks'], list(report['event_audit']['hint_checks'][0]))
    manifest = [{'split': split, 'id': row['id'], 'naviri': row['naviri']} for split, rows in splits.items() for row in rows]
    write_csv(destination / 'particiones_lm.csv', manifest, ['split', 'id', 'naviri'])
    # Diagnóstico por oración: probabilidad no equivale a confianza en una traducción.
    for split, rows in [('phase5', event['phase5']), ('lm_test', splits['test']), ('conversation', event['conversation'])]:
        scores = []
        for i, row in enumerate(rows, start=1):
            stats = lm.sentence_stats(tokenize(row['naviri']))
            scores.append({'id': row.get('id', f'CONV-{i:02}'), 'naviri': row['naviri'], **stats})
        write_csv(destination / f'scores_{split}.csv', scores, list(scores[0]))
    return report


if __name__ == '__main__':
    report = export_experiments()
    print('Eventos:', report['event_audit']['rows'])
    print('Particiones LM:', report['lm_split_sizes'])
    print('Modelo principal:', report['primary_model'])
