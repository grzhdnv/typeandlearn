"""Meaning-preserving hint normalization and exact source-occurrence coverage."""

import pathlib
import sys
import unittest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))
from schemas.texts import HintGroup
from services.hint_validation import normalize_hints


class HintValidationTests(unittest.TestCase):
    def hints(self, source, entries):
        return normalize_hints(source, [HintGroup(words=w, hint=h) for w, h in entries])

    def test_punctuation_unicode_apostrophes_and_phrase_entries(self):
        result = self.hints("¿Dónde está l’ora?", [(["Dónde está"], "where is"), (["l'ora"], "the time")])
        self.assertEqual([g.words for g in result], [["Dónde", "está"], ["l'ora"]])
        result = self.hints("l’ora", [(["l'", "ora"], "the time")])
        self.assertEqual(result[0].words, ["l'ora"])
        self.assertEqual(self.hints("e\u0301té!", [(["été"], "summer")])[0].words, ["été"])

    def test_unambiguous_case_is_normalized_but_lemmas_require_repair(self):
        result = self.hints("Ora vedo.", [(["ora"], "Now"), (["vedo"], "I see")])
        self.assertEqual(result[0].words, ["Ora"])
        with self.assertRaises(ValueError):
            self.hints("Ora vedo.", [(["Ora"], "Now"), (["vedere"], "I see")])

    def test_repeated_occurrences_are_preserved(self):
        result = self.hints("Bank Bank.", [(["Bank"], "bench"), (["Bank"], "bank")])
        self.assertEqual([g.hint for g in result], ["bench", "bank"])
        with self.assertRaises(ValueError):
            self.hints("Bank Bank.", [(["Bank"], "bench")])

    def test_missing_extra_empty_and_cross_group_contractions_are_rejected(self):
        cases = [
            ("Hallo Welt.", [(["Hallo"], "hello")]),
            ("Hallo.", [(["Hallo", "Hallo"], "hello")]),
            ("Hallo.", [(["Hallo"], " ")]),
            ("Hallo.", [([], "hello")]),
            ("j'avais su", [(["j'"], "I"), (["avais", "su"], "had known")]),
        ]
        for source, hints in cases:
            with self.subTest(source=source, hints=hints), self.assertRaises(ValueError):
                self.hints(source, hints)

    def test_separable_verb_group_does_not_require_contiguous_words(self):
        result = self.hints("Ich stehe früh auf.", [(["Ich"], "I"), (["stehe", "auf"], "get up"), (["früh"], "early")])
        self.assertEqual(result[1].words, ["stehe", "auf"])
