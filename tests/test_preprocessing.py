import unittest
from lexicon.preprocessing import normalize_exact_match, normalize_text, prepare, tokenize


class PreprocessingTests(unittest.TestCase):
    def test_preserves_linguistic_information(self):
        self.assertEqual(tokenize("  NU lomuta, lomuri.  "), ["nu", "lomuta", "lomuri"])
        self.assertEqual(tokenize("EL NIÑO no llevó el agua al RÍO."),
                         ["el", "niño", "no", "llevó", "el", "agua", "al", "río"])

    def test_unicode_and_evaluation_protocol(self):
        self.assertEqual(normalize_text("  RI\u0301O\t azul. "), "río azul.")
        self.assertEqual(normalize_exact_match("  NO, llegó...  "), "no, llegó")
        self.assertNotEqual(normalize_exact_match("no, llegó"), normalize_exact_match("no llegó"))

    def test_real_data_integrity_and_no_label_invention(self):
        processed, report = prepare()
        self.assertEqual(len(processed["public"]), 40)
        self.assertEqual(processed["public"][0]["id"], "NX-0001")
        self.assertNotIn("espanol", processed["public"][0])
        self.assertEqual(report["source_overlaps"]["train__validation"], 0)
        self.assertEqual(report["source_overlaps"]["monolingual__public"], 28)
        self.assertEqual(processed["train"][0]["naviri"], "vonu pira hala yelo.")


if __name__ == "__main__":
    unittest.main()
