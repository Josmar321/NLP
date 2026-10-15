"""EDA reproducible. Aprende categorías solo de train; el resto es diagnóstico.

Ejecutar: python -m lexicon.eda
"""
from __future__ import annotations

import csv
import base64
import hashlib
import json
import math
import os
import platform
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from lexicon.preprocessing import ROOT, FILES, normalize_exact_match, prepare

# Las dependencias compiladas deben pertenecer al entorno del kernel activo.
# Matplotlib se carga solo al graficar, no al importar las funciones de análisis.

SEED = 20261014
LABELS = {"train": "Entrenamiento", "validation": "Validación", "monolingual": "Monolingüe", "public": "Público"}
COLORS = ["#2563eb", "#e08021", "#158575", "#9960b8"]
PAIR_FIELDS = [("subject", "object"), ("subject", "root"), ("object", "root"),
               ("location", "root"), ("root", "tense")]
COMBINATIONS = [("subject", "object", "root"), ("object", "location", "root"),
                ("root", "tense", "negative"),
                ("subject", "object", "location", "negative", "root", "tense")]


def bilingual_parts(row):
    """Hipótesis explícita del español controlado; se contabilizan los rechazos."""
    return re.fullmatch(
        r"((?:el|la) \S+) (no )?(\S+) ((?:el|la) \S+)(?: en ((?:el|la) \S+))?",
        normalize_exact_match(row["espanol"]),
    )


def induce_categories(train):
    """Extrae lexicones posicionales. No se consulta validación ni público."""
    maps = {name: defaultdict(Counter) for name in ["subject", "object", "location", "verb"]}
    rejected, negation_disagreements = [], []
    for row in train:
        match = bilingual_parts(row)
        tokens = row["naviri_tokens"]
        if match is None or len(tokens) < 3:
            rejected.append(row["id"])
            continue
        subject, negative, verb, obj, location = match.groups()
        middle = [word for word in tokens[2:-1] if word != "nu"]
        if len(middle) != int(location is not None):
            rejected.append(row["id"])
            continue
        for category, word, target in [("subject", tokens[0], subject), ("object", tokens[1], obj), ("verb", tokens[-1], verb)]:
            maps[category][word][target] += 1
        if location is not None:
            maps["location"][middle[0]][location] += 1
        if bool(negative) != ("nu" in tokens):
            negation_disagreements.append(row["id"])
    # Morfología: -ta/-ri son hipótesis, aceptadas solo si existe la raíz en train.
    forms = set(maps["verb"])
    morphology = {}
    for word in sorted(forms):
        stem = word[:-2]
        if word.endswith("ta") and stem in forms:
            morphology[word] = (stem, "pasado")
        elif word.endswith("ri") and stem in forms:
            morphology[word] = (stem, "futuro")
        else:
            morphology[word] = (word, "presente")
    return maps, morphology, {"rejected_train_ids": rejected, "negation_disagreement_ids": negation_disagreements}


def parse_source(tokens, maps, morphology):
    """Aplica una hipótesis fija aprendida de train; no adivina tokens nuevos."""
    if len(tokens) < 3 or tokens[0] not in maps["subject"] or tokens[1] not in maps["object"] or tokens[-1] not in morphology:
        return None
    middle = tokens[2:-1]
    has_location = bool(middle and middle[0] in maps["location"])
    location = middle[0] if has_location else "∅"
    tail = middle[1:] if has_location else middle
    if tail not in ([], ["nu"]):
        return None
    root, tense = morphology[tokens[-1]]
    return {"subject": tokens[0], "object": tokens[1], "location": location,
            "negative": tail == ["nu"], "root": root, "tense": tense,
            "signature": "S O" + (" L" if has_location else "") + (" NEG" if tail else "") + " V"}


def ngrams(tokens, order):
    # Fronteras explícitas; no se cuentan n-gramas cruzando oraciones.
    padded = ["<s>"] * (order - 1) + tokens + ["</s>"]
    return [tuple(padded[i:i + order]) for i in range(len(padded) - order + 1)]


def js_divergence(left, right):
    """Divergencia Jensen-Shannon en bits, [0,1]; descriptiva, no test estadístico."""
    lt, rt = sum(left.values()), sum(right.values())
    result = 0.0
    for word in sorted(left.keys() | right.keys()):
        p, q = left.get(word, 0) / lt, right.get(word, 0) / rt
        mid = (p + q) / 2
        if p:
            result += 0.5 * p * math.log2(p / mid)
        if q:
            result += 0.5 * q * math.log2(q / mid)
    return result


def analyze(root=ROOT):
    data, audit = prepare(root)
    maps, morphology, evidence = induce_categories(data["train"])
    counts = {s: Counter(t for r in rows for t in r["naviri_tokens"]) for s, rows in data.items()}
    parsed = {s: [parse_source(r["naviri_tokens"], maps, morphology) for r in rows] for s, rows in data.items()}
    train_pairs = {f"{a}__{b}": {(p[a], p[b]) for p in parsed["train"] if p is not None} for a, b in PAIR_FIELDS}
    train_combos = {"__".join(fields): {tuple(p[f] for f in fields) for p in parsed["train"] if p is not None} for fields in COMBINATIONS}
    spanish_train = Counter(t for r in data["train"] for t in r["espanol_tokens"])
    lexicon = []
    for category, mappings in maps.items():
        for word, targets in sorted(mappings.items()):
            lexicon.append({"category": category, "source": word,
                            "targets": dict(targets), "support": sum(targets.values()),
                            "conflict": len(targets) > 1})
    conflicts = {}
    for s in ["train", "validation"]:
        grouped = defaultdict(set)
        for row in data[s]:
            grouped[normalize_exact_match(row["naviri"])].add(normalize_exact_match(row["espanol"]))
        conflicts[s] = sum(len(values) > 1 for values in grouped.values())
    metrics = {
        "seed": SEED, "python": platform.python_version(),
        "fit_split": "train", "audit": audit, "training_evidence": evidence,
        "lexicon": lexicon, "morphology": morphology, "conflicting_source_labels": conflicts,
        "file_sha256": {name: hashlib.sha256((Path(root) / "datos" / spec[0]).read_bytes()).hexdigest() for name, spec in FILES.items()},
        "splits": {}, "ngram_coverage": {},
    }
    for split, rows in data.items():
        parts = [p for p in parsed[split] if p is not None]
        lengths = [len(r["naviri_tokens"]) for r in rows]
        unseen_pairs = {}
        for a, b in PAIR_FIELDS:
            name = f"{a}__{b}"
            unseen_pairs[name] = {"unseen_rows": sum((p[a], p[b]) not in train_pairs[name] for p in parts),
                                  "parsed_rows": len(parts), "unique_train_pairs": len(train_pairs[name])}
        metrics["splits"][split] = {
            "rows": len(rows), "tokens": sum(lengths), "mean_length": sum(lengths) / len(rows),
            "vocabulary": len(counts[split]), "hapax": sum(n == 1 for n in counts[split].values()),
            "js_bits_vs_train": js_divergence(counts["train"], counts[split]),
            "parsed": len(parts), "unparsed_ids": [r["id"] for r, p in zip(rows, parsed[split]) if p is None],
            "signatures": dict(Counter(p["signature"] for p in parts)),
            "phenomena": {"negación": sum(p["negative"] for p in parts),
                          "pasado": sum(p["tense"] == "pasado" for p in parts),
                          "futuro": sum(p["tense"] == "futuro" for p in parts),
                          "locativo": sum(p["location"] != "∅" for p in parts)},
            "novel_pairs": unseen_pairs,
            "novel_combinations": {
                "__".join(fields): {"unseen_rows": sum(tuple(p[f] for f in fields) not in train_combos["__".join(fields)] for p in parts), "parsed_rows": len(parts)}
                for fields in COMBINATIONS
            },
        }
        if split in ["train", "validation"]:
            spanish = Counter(t for r in rows for t in r["espanol_tokens"])
            metrics["splits"][split]["spanish"] = {
                "tokens": sum(spanish.values()), "vocabulary": len(spanish),
                "oov_against_train": sorted(spanish.keys() - spanish_train.keys()),
            }
    public_sources = {normalize_exact_match(r["naviri"]) for r in data["public"]}
    clean_mono = [r for r in data["monolingual"] if normalize_exact_match(r["naviri"]) not in public_sources]
    metrics["monolingual_without_public"] = {"rows": len(clean_mono), "removed": len(data["monolingual"]) - len(clean_mono)}
    for order in [2, 3]:
        references = {s: Counter(ng for r in data[s] for ng in ngrams(r["naviri_tokens"], order)) for s in ["train", "monolingual"]}
        references["monolingual_without_public"] = Counter(ng for r in clean_mono for ng in ngrams(r["naviri_tokens"], order))
        metrics["ngram_coverage"][str(order)] = {}
        for split, rows in data.items():
            observed = Counter(ng for r in rows for ng in ngrams(r["naviri_tokens"], order))
            metrics["ngram_coverage"][str(order)][split] = {
                "unique": len(observed), "total_occurrences": sum(observed.values()),
                **{f"unseen_occurrence_rate_vs_{reference}": sum(n for ng, n in observed.items() if ng not in ref) / sum(observed.values()) for reference, ref in references.items()},
            }
    # Curvas por tamaño muestral, 20 permutaciones deterministas; no incertidumbre poblacional.
    growth = {}
    for split in ["train", "monolingual"]:
        rows = data[split]
        sizes = sorted({1, 10, 25, 50, 100, 200, len(rows)} | ({500, 1000, 2000} if len(rows) > 2000 else set()))
        curves = []
        for repeat in range(20):
            order = list(range(len(rows)))
            random.Random(SEED + repeat).shuffle(order)
            seen, curve = set(), {}
            for i, index in enumerate(order, start=1):
                seen.update(rows[index]["naviri_tokens"])
                if i in sizes:
                    curve[i] = len(seen)
            curves.append(curve)
        growth[split] = [{"sentences": n, "mean": sum(c[n] for c in curves) / len(curves),
                          "min": min(c[n] for c in curves), "max": max(c[n] for c in curves)} for n in sizes]
    metrics["vocabulary_growth"] = growth
    return data, counts, parsed, metrics


def make_figures(data, counts, parsed, metrics, destination):
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    metrics["matplotlib"] = matplotlib.__version__
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.titleweight": "bold"})
    images = []

    def save(fig, name):
        fig.savefig(destination / f"{name}.png", dpi=170, bbox_inches="tight")
        fig.savefig(destination / f"{name}.svg", bbox_inches="tight")
        images.append(name)
        plt.close(fig)

    splits = list(data)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), layout="constrained")
    for ax, field, title in zip(axes, ["rows", "tokens", "vocabulary"], ["Oraciones disponibles", "Tokens fuente", "Formas fuente distintas"]):
        vals = [metrics["splits"][s][field] for s in splits]
        bars = ax.bar([LABELS[s] for s in splits], vals, color=COLORS)
        ax.bar_label(bars, padding=3)
        ax.set_ylim(0, max(vals) * 1.2)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
    save(fig, "01_tamano_corpus")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for i, split in enumerate(splits):
        hist = Counter(len(r["naviri_tokens"]) for r in data[split])
        axes[0].bar([n + (i - 1.5) * 0.18 for n in [3, 4, 5]], [hist[n] / len(data[split]) * 100 for n in [3, 4, 5]], width=0.18, label=f"{LABELS[split]} (n={len(data[split])})", color=COLORS[i])
    axes[0].set(xticks=[3, 4, 5], xlabel="Tokens por oración fuente", ylabel="Oraciones (%)", title="Longitudes comparables por proporción")
    axes[0].legend(fontsize=8)
    for i, split in enumerate(["train", "validation"]):
        pairs = Counter((len(r["naviri_tokens"]), len(r["espanol_tokens"])) for r in data[split])
        axes[1].scatter([a + i * .07 for a, b in pairs], [b for a, b in pairs], s=[n * 8 for n in pairs.values()], alpha=.6, label=LABELS[split], color=COLORS[i])
    axes[1].set(xlabel="Tokens Eráviri", ylabel="Tokens español", title="Expansión al español (área = frecuencia)", xticks=[3, 4, 5])
    axes[1].legend()
    save(fig, "02_longitudes")

    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout="constrained")
    for ax, split, color in zip(axes, ["train", "monolingual"], [COLORS[0], COLORS[2]]):
        top = counts[split].most_common(20)[::-1]
        ax.barh([w for w, n in top], [n / sum(counts[split].values()) * 100 for w, n in top], color=color)
        ax.set(title=f"{LABELS[split]} · 20 formas más frecuentes", xlabel="Porcentaje de tokens fuente")
    save(fig, "03_frecuencias")

    categories = ["subject", "object", "location", "verb"]
    words = [r["source"] for category in categories for r in metrics["lexicon"] if r["category"] == category] + ["nu"]
    positions = ["Primera", "Segunda", "Intermedia", "Última"]
    position_counts = defaultdict(Counter)
    for row in data["train"]:
        tokens = row["naviri_tokens"]
        for i, word in enumerate(tokens):
            label = "Primera" if i == 0 else "Segunda" if i == 1 else "Última" if i == len(tokens) - 1 else "Intermedia"
            position_counts[word][label] += 1
    matrix = [[position_counts[w][p] / sum(position_counts[w].values()) for p in positions] for w in words]
    fig, ax = plt.subplots(figsize=(7, 13), layout="constrained")
    im = ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set(yticks=range(len(words)), yticklabels=words, xticks=range(4), xticklabels=positions, title="Posición por forma · solo entrenamiento")
    ax.tick_params(axis="y", labelsize=8)
    fig.colorbar(im, ax=ax, label="Proporción de apariciones de cada forma")
    save(fig, "04_posiciones")

    phenomena = ["negación", "pasado", "futuro", "locativo"]
    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    for i, split in enumerate(splits):
        info = metrics["splits"][split]
        bars = ax.bar([n + (i - 1.5) * .19 for n in range(4)], [info["phenomena"][p] / info["rows"] * 100 for p in phenomena], width=.19, color=COLORS[i], label=f"{LABELS[split]} (n={info['rows']})")
        ax.bar_label(bars, labels=[str(info["phenomena"][p]) for p in phenomena], fontsize=8, padding=3)
    ax.set(xticks=range(4), xticklabels=phenomena, ylabel="Porcentaje de oraciones", ylim=(0, 100), title="Fenómenos según hipótesis de train · etiquetas = conteos")
    ax.legend(ncols=2, fontsize=9)
    save(fig, "05_fenomenos")

    sources = {s: {normalize_exact_match(r["naviri"]) for r in rows} for s, rows in data.items()}
    mat = [[len(sources[a] & sources[b]) for b in splits] for a in splits]
    fig, ax = plt.subplots(figsize=(7, 6), layout="constrained")
    im = ax.imshow([[0 if i == j else mat[i][j] for j in range(4)] for i in range(4)], cmap="Oranges", vmin=0, vmax=40)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, str(mat[i][j]), ha="center", va="center")
    ax.set(xticks=range(4), xticklabels=[LABELS[s] for s in splits], yticks=range(4), yticklabels=[LABELS[s] for s in splits], title="Fuentes compartidas · diagonal = fuentes propias")
    ax.tick_params(axis="x", rotation=25)
    fig.colorbar(im, ax=ax, label="Coincidencias entre particiones (diagonal sin escala)")
    save(fig, "06_cruces")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), layout="constrained")
    for split, color in [("train", COLORS[0]), ("monolingual", COLORS[2])]:
        curve = metrics["vocabulary_growth"][split]
        x = [p["sentences"] for p in curve]
        axes[0].plot(x, [p["mean"] for p in curve], marker="o", color=color, label=LABELS[split])
        axes[0].fill_between(x, [p["min"] for p in curve], [p["max"] for p in curve], alpha=.15, color=color)
    axes[0].set(xscale="log", xlabel="Oraciones muestreadas (escala log)", ylabel="Formas distintas", title="Cobertura léxica · 20 órdenes aleatorios")
    axes[0].legend()
    for i, order in enumerate([2, 3]):
        vals = [metrics["ngram_coverage"][str(order)][s]["unseen_occurrence_rate_vs_train"] * 100 for s in splits]
        bars = axes[1].bar([n + (i - .5) * .35 for n in range(4)], vals, width=.35, label=f"{order}-gramas")
        axes[1].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[1].set(xticks=range(4), xticklabels=[LABELS[s] for s in splits], ylabel="Ocurrencias no vistas en train (%)", title="N-gramas nuevos pese a vocabulario conocido")
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].legend()
    save(fig, "07_cobertura_ngramas")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for i, split in enumerate(["validation", "public"]):
        info = metrics["splits"][split]["novel_pairs"]
        vals = [info[f"{a}__{b}"]["unseen_rows"] / max(info[f"{a}__{b}"]["parsed_rows"], 1) * 100 for a, b in PAIR_FIELDS]
        bars = axes[0].bar([n + (i - .5) * .35 for n in range(5)], vals, width=.35, label=LABELS[split], color=COLORS[1 if split == "validation" else 3])
        axes[0].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[0].set(xticks=range(5), xticklabels=["Sujeto–objeto", "Sujeto–raíz", "Objeto–raíz", "Lugar–raíz", "Raíz–tiempo"], ylabel="Oraciones con pareja nueva (%)", title="Novedad composicional respecto a train")
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].legend()
    roots = sorted({root for root, tense in metrics["morphology"].values()})
    forms = metrics["morphology"]
    temporal = [[sum(counts["train"][w] for w, (r, t) in forms.items() if r == root and t == tense) for tense in ["presente", "pasado", "futuro"]] for root in roots]
    im = axes[1].imshow(temporal, cmap="YlGnBu", aspect="auto")
    for i, row in enumerate(temporal):
        for j, value in enumerate(row):
            axes[1].text(j, i, str(value), ha="center", va="center", color="white" if value > 25 else "black")
    axes[1].set(yticks=range(len(roots)), yticklabels=roots, xticks=range(3), xticklabels=["Presente", "Pasado", "Futuro"], title="Soporte de formas verbales · train")
    fig.colorbar(im, ax=axes[1], label="Apariciones")
    save(fig, "08_composicion_morfologia")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    labels = ["Sujeto–objeto–raíz", "Objeto–lugar–raíz", "Raíz–tiempo–negación", "Configuración completa"]
    for i, split in enumerate(["validation", "public"]):
        info = metrics["splits"][split]["novel_combinations"]
        values = [info["__".join(fields)]["unseen_rows"] / metrics["splits"][split]["parsed"] * 100 for fields in COMBINATIONS]
        bars = axes[0].bar([n + (i - .5) * .35 for n in range(4)], values, width=.35, color=COLORS[1 if split == "validation" else 3], label=LABELS[split])
        axes[0].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[0].set(xticks=range(4), xticklabels=labels, ylabel="Oraciones con combinación no vista (%)", ylim=(0, 115), title="Las parejas no bastan para medir composición")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].legend()
    signatures = ["S O V", "S O NEG V", "S O L V", "S O L NEG V"]
    for i, split in enumerate(splits):
        info = metrics["splits"][split]
        axes[1].bar([n + (i - 1.5) * .18 for n in range(4)], [info["signatures"].get(s, 0) / info["rows"] * 100 for s in signatures], width=.18, color=COLORS[i], label=LABELS[split])
    axes[1].set(xticks=range(4), xticklabels=signatures, ylabel="Porcentaje de oraciones", title="Cuatro plantillas observadas")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].legend(fontsize=8)
    save(fig, "09_novedad_plantillas")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), layout="constrained")
    refs = ["train", "monolingual", "monolingual_without_public"]
    for ax, split in zip(axes, ["validation", "public"]):
        for i, ref in enumerate(refs):
            vals = [metrics["ngram_coverage"][str(order)][split][f"unseen_occurrence_rate_vs_{ref}"] * 100 for order in [2, 3]]
            bars = ax.bar([n + (i - 1) * .25 for n in range(2)], vals, width=.25, label=["Train", "Mono completo", "Mono sin público"][i], color=[COLORS[0], COLORS[2], COLORS[3]][i])
            ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
        ax.set(xticks=[0, 1], xticklabels=["Bigramas", "Trigramas"], ylabel="Ocurrencias no vistas (%)", title=f"{LABELS[split]} · cobertura según corpus de referencia")
        ax.legend(fontsize=8)
    save(fig, "10_aporte_monolingue")
    return images


def export_eda(root=ROOT):
    data, counts, parsed, metrics = analyze(root)
    destination = Path(root) / "resultados" / "eda"
    destination.mkdir(parents=True, exist_ok=True)
    images = make_figures(data, counts, parsed, metrics, destination)
    metrics["figures"] = images
    (destination / "metricas.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for split, rows in data.items():
        with (destination / f"estructura_{split}.csv").open("w", encoding="utf-8", newline="") as handle:
            fields = ["id", "subject", "object", "location", "negative", "root", "tense", "signature"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row, parts in zip(rows, parsed[split]):
                writer.writerow({"id": row["id"], **(parts or {})})
    with (destination / "lexico_train.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "source", "targets", "support", "conflict"])
        writer.writeheader()
        writer.writerows({**r, "targets": json.dumps(r["targets"], ensure_ascii=False)} for r in metrics["lexicon"])
    descriptions = [
        "Tamaños absolutos: no comparar frecuencias brutas entre corpus de distinto tamaño.",
        "Longitudes normalizadas por partición y expansión de Eráviri al español.",
        "Frecuencias relativas. Las formas verbales conservan sus sufijos.",
        "Posiciones observadas solo en entrenamiento; evidencia a favor de categorías separadas.",
        "Los fenómenos pueden solaparse. Público tiene solo 40 ejemplos; no inferir diferencias poblacionales.",
        "Hay 28 fuentes públicas en monolingüe, sin traducciones españolas.",
        "El vocabulario se satura, pero persisten contextos nuevos. Banda: mínimo/máximo de 20 permutaciones, no intervalo de confianza.",
        "Las parejas se comparan contra entrenamiento; ∅ cuenta como ausencia de lugar. Kori es una raíz en presente.",
        "Configuraciones nuevas no implican palabras nuevas ni prueban por sí solas un cambio de distribución.",
        "Cobertura de contextos, no exactitud de traducción. Mono sin público elimina las 28 coincidencias exactas.",
    ]
    cards = []
    for name, description in zip(images, descriptions):
        encoded = base64.b64encode((destination / f"{name}.png").read_bytes()).decode("ascii")
        cards.append(f'<section><h2>{name.replace("_", " ")}</h2><p>{description}</p><img alt="{description}" src="data:image/png;base64,{encoded}"></section>')
    html = '''<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LEXICON-X · Exploración de corpus</title>
<style>body{font:16px/1.6 system-ui,sans-serif;background:#eef2f6;color:#172b40;max-width:1200px;margin:auto;padding:30px}section,header{background:white;padding:24px;margin:20px 0;border-radius:12px}img{max-width:100%;height:auto}h1,h2{line-height:1.2}small{color:#526475}</style>
<header><small>LEXICON-X · EDA reproducible</small><h1>Conocer palabras no basta para traducir combinaciones nuevas</h1>
<p>420 pares de entrenamiento · 120 de validación · 3.000 mensajes monolingües · 40 públicos.</p>
<p>Las 59 formas fuente ya están en entrenamiento. 87/120 ejemplos de validación y 34/40 públicos tienen una terna sujeto–objeto–raíz nueva. Los 28 cruces público–monolingüe requieren declarar exposición transductiva.</p>
<p>Categorías y correspondencias inducidas solo de entrenamiento. Los otros conjuntos se usan para diagnóstico; no se generan traducciones. Interpretación y decisiones: EDA_CORPUS.md en la raíz.</p></header>'''
    (destination / "informe_visual.html").write_text(html + "".join(cards) + "</html>", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    report = export_eda()
    for split, info in report["splits"].items():
        print(f"{split}: {info['rows']} filas; {info['vocabulary']} formas; {info['parsed']} estructuras reconocidas")
    print("Gráficos y tablas:", ROOT / "resultados" / "eda")
