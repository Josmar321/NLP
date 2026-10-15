"""Modelos probabilísticos de palabras con suavizado y fronteras explícitas.

Solo biblioteca estándar. No aprende traducciones.
"""
from __future__ import annotations

import math
import json
from collections import Counter
from pathlib import Path

BOS, EOS, UNK = '<s>', '</s>', '<unk>'


class NGramLM:
    def __init__(self, order=2, alpha=0.1, weights=None):
        if order not in (1, 2, 3) or alpha <= 0:
            raise ValueError('order debe ser 1, 2 o 3; alpha debe ser positivo')
        if weights is not None and (len(weights) != order or any(w < 0 for w in weights) or not math.isclose(sum(weights), 1)):
            raise ValueError('Los pesos deben ser no negativos y sumar uno')
        self.order, self.alpha, self.weights = order, alpha, weights
        self.fitted = False

    def fit(self, sentences, vocabulary=None):
        sentences = [list(tokens) for tokens in sentences]
        if not sentences or any(not tokens for tokens in sentences):
            raise ValueError('Se necesitan oraciones no vacías')
        lexical = set(vocabulary) if vocabulary is not None else {w for sent in sentences for w in sent}
        if lexical & {BOS, EOS, UNK}:
            raise ValueError('Los tokens reservados no deben aparecer en el vocabulario léxico')
        self.lexical_vocabulary = frozenset(lexical)
        self.vocabulary = tuple(sorted(lexical | {EOS, UNK}))
        self.counts, self.context_counts = {}, {}
        for k in range(1, self.order + 1):
            counts, contexts = Counter(), Counter()
            for sent in sentences:
                words = [BOS] * (k - 1) + [self.map_token(w) for w in sent] + [EOS]
                for i in range(k - 1, len(words)):
                    history = tuple(words[i - k + 1:i]) if k > 1 else ()
                    counts[history + (words[i],)] += 1
                    contexts[history] += 1
            self.counts[k], self.context_counts[k] = counts, contexts
        self.fitted = True
        return self

    def map_token(self, token):
        return token if token in self.lexical_vocabulary else UNK

    def probability(self, token, history=()):
        if not self.fitted:
            raise ValueError('Primero ejecutar fit')
        if token == BOS:
            return 0.0
        target = token if token in (EOS, UNK) else self.map_token(token)
        mapped = [BOS if w == BOS else self.map_token(w) for w in history]

        def component(k):
            ctx = tuple(([BOS] * (k - 1) + mapped)[-(k - 1):]) if k > 1 else ()
            return (self.counts[k][ctx + (target,)] + self.alpha) / (self.context_counts[k][ctx] + self.alpha * len(self.vocabulary))

        if self.weights is None:
            return component(self.order)
        return sum(w * component(k) for k, w in enumerate(self.weights, start=1))

    def sentence_stats(self, tokens):
        tokens = list(tokens)
        history, nll = [], 0.0
        for word in tokens + [EOS]:
            nll -= math.log(self.probability(word, history))
            history.append(word)
        return {'nll': nll, 'predicted_tokens': len(tokens) + 1,
                'lexical_tokens': len(tokens),
                'oov_tokens': sum(w not in self.lexical_vocabulary for w in tokens)}

    def evaluate(self, sentences):
        stats = [self.sentence_stats(s) for s in sentences]
        if not stats:
            raise ValueError('No se evalúa un conjunto vacío')
        nll = sum(r['nll'] for r in stats)
        n = sum(r['predicted_tokens'] for r in stats)
        lexical = sum(r['lexical_tokens'] for r in stats)
        oov = sum(r['oov_tokens'] for r in stats)
        return {'sentences': len(stats), 'predicted_tokens': n, 'lexical_tokens': lexical,
                'oov_tokens': oov, 'oov_rate': oov / lexical if lexical else 0.0,
                'cross_entropy_nats': nll / n, 'cross_entropy_bits': nll / n / math.log(2),
                'perplexity': math.exp(nll / n)}

    def save(self, path):
        if not self.fitted:
            raise ValueError('Primero ejecutar fit')
        state = {'format_version': 1, 'order': self.order, 'alpha': self.alpha,
                 'weights': self.weights, 'lexical_vocabulary': sorted(self.lexical_vocabulary),
                 'counts': {str(k): [[list(ng), count] for ng, count in sorted(counts.items())]
                            for k, counts in self.counts.items()}}
        Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    @classmethod
    def load(cls, path):
        state = json.loads(Path(path).read_text(encoding='utf-8'))
        if state['format_version'] != 1:
            raise ValueError('Formato de modelo no compatible')
        model = cls(state['order'], state['alpha'], state['weights'])
        model.lexical_vocabulary = frozenset(state['lexical_vocabulary'])
        if model.lexical_vocabulary & {BOS, EOS, UNK}:
            raise ValueError('Vocabulario de modelo inválido')
        model.vocabulary = tuple(sorted(model.lexical_vocabulary | {EOS, UNK}))
        model.counts, model.context_counts = {}, {}
        for k in range(1, model.order + 1):
            counts, contexts = Counter(), Counter()
            for ngram, count in state['counts'][str(k)]:
                if len(ngram) != k or not isinstance(count, int) or count <= 0 or ngram[-1] not in model.vocabulary or any(t not in model.vocabulary and t != BOS for t in ngram[:-1]):
                    raise ValueError('Conteo de modelo inválido')
                counts[tuple(ngram)] += count
                contexts[tuple(ngram[:-1])] += count
            model.counts[k], model.context_counts[k] = counts, contexts
        model.fitted = True
        return model
