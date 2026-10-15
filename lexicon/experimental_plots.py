"""Figuras de experimentos ya calculados; no selecciona ni ajusta modelos."""
import csv
import json
import os
from pathlib import Path
from lexicon.preprocessing import ROOT


def plot_experiments(root=ROOT):
    root = Path(root)
    destination = root / 'resultados' / 'experimental_03'
    metrics = json.loads((destination / 'metricas.json').read_text(encoding='utf-8'))
    with (destination / 'busqueda_dev.csv').open(encoding='utf-8', newline='') as f:
        search = list(csv.DictReader(f))
    os.environ.setdefault('MPLCONFIGDIR', str(root / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    families = ['unigram', 'bigram', 'trigram', 'interpolated']
    labels = ['Unigrama', 'Bigrama', 'Trigrama', 'Interpolado']
    images = []

    def save(fig, name):
        fig.savefig(destination / f'{name}.png', dpi=170, bbox_inches='tight')
        fig.savefig(destination / f'{name}.svg', bbox_inches='tight')
        images.append(name)
        plt.close(fig)

    main = [next(r for r in metrics['selected'] if r['condition'] == 'mono_clean' and r['family'] == family) for family in families]
    fig, ax = plt.subplots(figsize=(10, 5), layout='constrained')
    for i, field in enumerate(['dev', 'test']):
        values = [r['dev_perplexity'] if field == 'dev' else r['test']['perplexity'] for r in main]
        bars = ax.bar([x + (i - .5) * .35 for x in range(4)], values, width=.35, color=['#2563eb', '#158575'][i], label=['Desarrollo: selecciona', 'Prueba: evalúa'][i])
        ax.bar_label(bars, fmt='%.2f', padding=3)
    ax.set(xticks=range(4), xticklabels=labels, ylabel='Perplejidad · menor es mejor', title='Comparación principal · mismo vocabulario, particiones y EOS', ylim=(0, 43))
    ax.legend()
    save(fig, '01_modelos_dev_test')

    fig, ax = plt.subplots(figsize=(10, 5), layout='constrained')
    alphas = [.01, .05, .1, .5, 1]
    for family, label in zip(families, labels):
        values = [min(float(r['dev_perplexity']) for r in search if r['condition'] == 'mono_clean' and r['family'] == family and float(r['alpha']) == alpha) for alpha in alphas]
        ax.plot(alphas, values, marker='o', label=label)
    ax.set(xscale='log', xlabel='Alpha de suavizado (escala log)', ylabel='Perplejidad de desarrollo', title='Elegir parámetros con desarrollo · sin usar prueba')
    ax.legend()
    save(fig, '02_suavizado_dev')

    rows = metrics['fixed_bigram_ablation']
    names = {'train_420': 'Pares fuente\n420', 'mono_clean': 'Mono limpio\n2.377', 'train_plus_mono': 'Pares + mono\n2.797', 'mono_transductive': 'Mono + exposición\n2.405', 'mono_sample_420': 'Muestra mono\n420'}
    fig, ax = plt.subplots(figsize=(12, 5), layout='constrained')
    for i, field in enumerate(['dev_perplexity', 'test_perplexity']):
        bars = ax.bar([x + (i - .5) * .35 for x in range(len(rows))], [r[field] for r in rows], width=.35, color=['#2563eb', '#158575'][i], label=['Desarrollo', 'Prueba'][i])
        ax.bar_label(bars, fmt='%.2f', padding=3, fontsize=9)
    ax.set(xticks=range(len(rows)), xticklabels=[names[r['condition']] for r in rows], ylabel='Perplejidad', title='Comparación de corpus · bigrama y alpha=0,01 fijos')
    ax.set_ylim(0, max(r['test_perplexity'] for r in rows) * 1.25)
    ax.legend()
    save(fig, '03_corpus_controlado')

    external = metrics['external_diagnostics']
    keys = ['validation_source', 'public_source', 'phase5_source', 'conversation_shift']
    names = ['Validación\nfuente', 'Público\nfuente', 'Fase 5', 'Conversación']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    values = [external[k]['perplexity'] for k in keys]
    bars = axes[0].bar(names, values, color=['#2563eb', '#158575', '#9960b8', '#e08021'])
    axes[0].bar_label(bars, fmt='%.2f', padding=4)
    axes[0].set(yscale='log', ylabel='Perplejidad (escala log)', title='Diagnósticos del modelo principal congelado', ylim=(1, max(values) * 2.5))
    bars = axes[1].bar(names, [external[k]['oov_rate'] * 100 for k in keys], color=['#2563eb', '#158575', '#9960b8', '#e08021'])
    axes[1].bar_label(bars, labels=[f"{external[k]['oov_tokens']}/{external[k]['lexical_tokens']}" for k in keys], padding=4)
    axes[1].set(ylabel='Tokens fuera del vocabulario (%)', title='Conversación: otro vocabulario y otras estructuras', ylim=(0, 110))
    save(fig, '04_evento_cambio_dominio')

    with (destination / 'scores_phase5.csv').open(encoding='utf-8', newline='') as f:
        scores = list(csv.DictReader(f))
    import math
    ranked = sorted(scores, key=lambda r: float(r['nll']) / int(r['predicted_tokens']), reverse=True)[:12][::-1]
    fig, ax = plt.subplots(figsize=(12, 7), layout='constrained')
    ax.barh([f"{r['id']}  {r['naviri']}" for r in ranked], [float(r['nll']) / int(r['predicted_tokens']) / math.log(2) for r in ranked], color='#9960b8')
    ax.set(xlabel='Sorpresa media por token predicho (bits, incluye EOS)', title='Fase 5 · doce mensajes menos probables para el LM\nLa probabilidad mide familiaridad, no exactitud de traducción')
    save(fig, '05_fase5_sorpresa')
    (destination / 'figuras.json').write_text(json.dumps({'matplotlib': matplotlib.__version__, 'figures': images}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return images


if __name__ == '__main__':
    print(plot_experiments())
