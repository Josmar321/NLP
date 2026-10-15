"""Preprocesamiento sin aprendizaje ni modificación de los CSV originales.

No elimina stopwords, tildes, negación ni sufijos. No aplica stemming.
"""
from __future__ import annotations

import csv
import json
import platform
import unicodedata
from collections import Counter
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "train": ("train_parallel.csv", 420, True),
    "validation": ("validation_parallel.csv", 120, True),
    "monolingual": ("corpus_monolingual.csv", 3000, False),
    "public": ("test_public_unlabeled.csv", 40, False),
}


def normalize_text(text: str) -> str:
    """NFC, minúsculas y espacios; conserva puntuación y contenido lingüístico."""
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def normalize_exact_match(text: str) -> str:
    """Protocolo del enunciado: quita únicamente puntuación final."""
    text = normalize_text(text)
    while text and unicodedata.category(text[-1]).startswith("P"):
        text = text[:-1].rstrip()
    return text


def tokenize(text: str) -> list[str]:
    """Separa puntuación sin borrar ni truncar palabras con tildes o sufijos."""
    text = normalize_text(text)
    return "".join(
        " " if unicodedata.category(c).startswith("P") else c for c in text
    ).split()


def load_datasets(root: Path = ROOT) -> dict[str, list[dict[str, str]]]:
    datasets = {}
    for split, (filename, expected, parallel) in FILES.items():
        path = Path(root) / "datos" / filename
        columns = ["id", "naviri"] + (["espanol"] if parallel else [])
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns:
                raise ValueError(f"{path}: columnas esperadas {columns}, recibidas {reader.fieldnames}")
            rows = list(reader)
        if len(rows) != expected:
            raise ValueError(f"{path}: se esperaban {expected} filas; hay {len(rows)}")
        seen = set()
        for index, row in enumerate(rows, start=2):
            if set(row) != set(columns) or any(
                not isinstance(row.get(key), str) or not row[key].strip() for key in columns
            ):
                raise ValueError(f"{path}:{index}: fila incompleta o mal formada")
            if row["id"] in seen:
                raise ValueError(f"{path}:{index}: ID repetido {row['id']}")
            seen.add(row["id"])
            for field in columns[1:]:
                if not tokenize(row[field]):
                    raise ValueError(f"{path}:{index}: {field} sin tokens")
        datasets[split] = rows
    return datasets


def preprocess_row(row: dict[str, str]) -> dict:
    result = dict(row)
    for field in ("naviri", "espanol"):
        if field in row:
            result[f"{field}_normalizado"] = normalize_text(row[field])
            result[f"{field}_tokens"] = tokenize(row[field])
    return result


def prepare(root: Path = ROOT) -> tuple[dict, dict]:
    datasets = load_datasets(root)
    processed = {key: [preprocess_row(row) for row in rows] for key, rows in datasets.items()}
    # Solo entrenamiento define el vocabulario de referencia; nunca se aprende de validación.
    train_vocab = {token for row in processed["train"] for token in row["naviri_tokens"]}
    report = {
        "python": platform.python_version(),
        "policy": "NFC, minúsculas, espacios; tokens superficiales; sin stopwords ni stemming",
        "vocabulary_fit_split": "train",
        "splits": {},
        "source_overlaps": {},
    }
    sources = {}
    for split, rows in processed.items():
        counts = Counter(token for row in rows for token in row["naviri_tokens"])
        sources[split] = {normalize_exact_match(row["naviri"]) for row in rows}
        report["splits"][split] = {
            "rows": len(rows),
            "unique_sources_normalized": len(sources[split]),
            "vocabulary_size": len(counts),
            "oov_against_train": sorted(set(counts) - train_vocab),
            "lengths": dict(sorted(Counter(len(row["naviri_tokens"]) for row in rows).items())),
            "token_frequencies": dict(counts.most_common()),
        }
    for left, right in combinations(sources, 2):
        report["source_overlaps"][f"{left}__{right}"] = len(sources[left] & sources[right])
    return processed, report


def export_preprocessed(root: Path = ROOT) -> dict:
    processed, report = prepare(root)
    destination = Path(root) / "resultados" / "preprocesamiento"
    destination.mkdir(parents=True, exist_ok=True)
    for split, rows in processed.items():
        with (destination / f"{split}.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (destination / "auditoria.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    audit = export_preprocessed()
    for split, summary in audit["splits"].items():
        print(f"{split}: {summary['rows']} filas, {summary['vocabulary_size']} formas")
    print("Resultados:", ROOT / "resultados" / "preprocesamiento")
