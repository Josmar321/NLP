import unittest
from lexicon.preprocessing import prepare, normalize_exact_match
from lexicon.experimental import load_event, inspect_event, partition_monolingual


class ExperimentalTests(unittest.TestCase):
    def test_event_roles_and_training_contrast(self):
        data, _ = prepare()
        event = load_event()
        audit = inspect_event(data, event)
        self.assertEqual(audit['rows'], {'conversation': 18, 'phase5': 40, 'hints': 21})
        self.assertEqual(audit['hints_consistent'], 21)
        self.assertEqual(len(audit['conversation_new_types']), 15)
        self.assertEqual(audit['phase5_oov_types'], [])
        self.assertEqual(audit['phase5_parsed'], 40)
        self.assertTrue(any(r['naviri'] == '-ri' for r in event['hints']))

    def test_reproducible_split_and_no_target_exposure(self):
        data, _ = prepare()
        event = load_event()
        splits, excluded = partition_monolingual(data, event)
        repeat, _ = partition_monolingual(data, event)
        self.assertEqual(splits, repeat)
        self.assertEqual(sum(map(len, splits.values())), 2972)
        self.assertEqual(len(excluded), 28)
        forbidden = {normalize_exact_match(r['naviri']) for r in data['public'] + event['phase5']}
        seen = set()
        for rows in splits.values():
            sources = {normalize_exact_match(r['naviri']) for r in rows}
            self.assertFalse(sources & forbidden)
            self.assertFalse(sources & seen)
            seen.update(sources)


if __name__ == '__main__':
    unittest.main()
