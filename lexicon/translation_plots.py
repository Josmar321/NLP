"""Gráficos de la evaluación de traducción, sin ajustar modelos."""
import ast
import csv
import json
import os
from collections import Counter
from pathlib import Path
from lexicon.preprocessing import ROOT


def plot_translation(root=ROOT):
    root = Path(root)
    destination = root / 'resultados' / 'traduccion_04'
    report = json.loads((destination / 'metricas.json').read_text(encoding='utf-8'))
    os.environ.setdefault('MPLCONFIGDIR', str(root / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    names = ['jaccard', 'compositional', 'without_tense', 'without_negation', 'without_reordering']
    labels = ['Jaccard', 'Composicional', 'Sin tiempo', 'Sin negación', 'Sin reordenar']
    colors = ['#e08021', '#158575', '#9960b8', '#c75c70', '#64748b']
    figures = []

    def save(fig, name):
        fig.savefig(destination / f'{name}.png', dpi=170, bbox_inches='tight')
        fig.savefig(destination / f'{name}.svg', bbox_inches='tight')
        figures.append(name)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    for ax, field, title in zip(axes, ['exact_match', 'chrf'], ['Exact match normalizado (%)', 'chrF de sacrebleu (0–100)']):
        values = [report['validation_results'][name]['groups']['all'][field] * (100 if field == 'exact_match' else 1) for name in names]
        bars = ax.bar(labels, values, color=colors)
        ax.bar_label(bars, fmt='%.2f', padding=4, fontsize=9)
        ax.set(title=title, ylim=(0, 115))
        ax.tick_params(axis='x', rotation=25)
    fig.suptitle('Validación · 120 pares · parámetros y léxico fijados con entrenamiento')
    save(fig, '01_comparacion_metricas')

    groups = ['negation', 'past', 'future', 'present', 'location', 'without_location', 'novel_triple', 'seen_triple']
    group_labels = ['Negación', 'Pasado', 'Futuro', 'Presente', 'Con lugar', 'Sin lugar', 'Terna nueva', 'Terna vista']
    matrix = [[100 * report['validation_results'][name]['groups'][g]['exact_match'] for g in groups] for name in names]
    fig, ax = plt.subplots(figsize=(12, 5.5), layout='constrained')
    im = ax.imshow(matrix, cmap='YlGnBu', vmin=0, vmax=100, aspect='auto')
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax.text(j, i, f'{value:.1f}', ha='center', va='center', color='white' if value > 65 else 'black')
    ax.set(yticks=range(len(names)), yticklabels=labels, xticks=range(len(groups)),
           xticklabels=[f"{label}\nn={report['validation_results']['compositional']['groups'][g]['n']}" for g, label in zip(groups, group_labels)],
           title='Exact match por fenómeno · grupos solapados, tamaños diferentes')
    ax.tick_params(axis='x', rotation=20)
    fig.colorbar(im, ax=ax, label='Exact match (%)')
    save(fig, '02_fenomenos_composicion')

    with (destination / 'errores.csv').open(encoding='utf-8', newline='') as f:
        errors = list(csv.DictReader(f))
    counts = Counter(error for row in errors if row['system'] == 'jaccard' for error in ast.literal_eval(row['error_types']))
    fig, ax = plt.subplots(figsize=(10, 5), layout='constrained')
    top = counts.most_common()[::-1]
    bars = ax.barh([name for name, n in top], [n for name, n in top], color='#e08021')
    ax.bar_label(bars, padding=4)
    ax.set(xlabel='Oraciones con ese tipo de error', title='Errores del baseline · una oración puede tener varios tipos')
    ax.set_xlim(0, max(counts.values()) * 1.15)
    save(fig, '03_errores_baseline')
    (destination / 'figuras.json').write_text(json.dumps({'matplotlib': matplotlib.__version__, 'figures': figures}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return figures


if __name__ == '__main__':
    print(plot_translation())
