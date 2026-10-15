import math
import unittest
import tempfile
from pathlib import Path
from lexicon.ngram import NGramLM, BOS, EOS, UNK


class NGramTests(unittest.TestCase):
    def test_add_alpha_probability_and_normalization(self):
        model = NGramLM(2, alpha=1).fit([['a', 'b'], ['a', 'a']])
        self.assertAlmostEqual(model.probability('a', []), 3 / 6)
        self.assertAlmostEqual(model.probability('b', ['a']), 2 / 7)
        for context in [[], ['a'], ['not_seen'], ['b', 'a']]:
            self.assertAlmostEqual(sum(model.probability(w, context) for w in model.vocabulary), 1)
        self.assertEqual(model.probability(BOS), 0)

    def test_boundaries_unknown_and_manual_perplexity(self):
        model = NGramLM(1, alpha=1).fit([['a']])
        # a=1, EOS=1, UNK=0; denominador 2+3.
        self.assertAlmostEqual(model.probability('a'), 2 / 5)
        self.assertAlmostEqual(model.probability('new'), 1 / 5)
        metrics = model.evaluate([['a']])
        self.assertAlmostEqual(metrics['perplexity'], 2.5)
        self.assertEqual(metrics['predicted_tokens'], 2)
        self.assertNotIn('new', model.lexical_vocabulary)
        self.assertEqual(model.evaluate([['new']])['oov_rate'], 1)

    def test_no_cross_sentence_context_and_interpolation(self):
        model = NGramLM(3, .1, (.1, .3, .6)).fit([['a'], ['b']])
        self.assertEqual(model.counts[2][('a', 'b')], 0)
        self.assertEqual(model.counts[3][(BOS, BOS, 'a')], 1)
        self.assertAlmostEqual(sum(model.probability(w, ['unseen']) for w in model.vocabulary), 1)
        self.assertTrue(math.isfinite(model.evaluate([['new', 'a']])['perplexity']))
        with self.assertRaises(ValueError):
            NGramLM(3, .1, (.1, .3, .5))

    def test_saved_model_preserves_probabilities_without_training(self):
        model = NGramLM(3, .1, (.1, .3, .6)).fit([['a', 'b'], ['a', 'a']])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.json'
            model.save(path)
            loaded = NGramLM.load(path)
            self.assertEqual(model.evaluate([['a', 'unknown']]), loaded.evaluate([['a', 'unknown']]))
            self.assertEqual(model.counts, loaded.counts)


if __name__ == '__main__':
    unittest.main()
