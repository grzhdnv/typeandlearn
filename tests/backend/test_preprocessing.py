"""Exercise installed language pipelines and missing-model diagnostics."""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from services import preprocessing_service


class PreprocessingTests(unittest.TestCase):
    """Use real model packages so an incomplete bootstrap fails in CI."""

    def test_supported_language_pipelines(self) -> None:
        samples = (
            ("German", "Der kleine Hund läuft im Garten. Die Sonne scheint.",
             "Hund"),
            ("French", "Le petit chat dort dans le jardin. Le soleil brille.",
             "chat"),
            ("Italian", "Il piccolo gatto dorme in giardino. Il sole splende.",
             "gatto"),
            ("Spanish", "El pequeño gato duerme en el jardín. El sol brilla.",
             "gato"),
            ("English", "The small cat sleeps in the garden. The sun shines.",
             "cat"),
        )
        service = preprocessing_service.PreprocessingService()
        for language, text, expected_word in samples:
            with self.subTest(language=language):
                paragraphs, frequencies = service.process_text(text, language)
                self.assertEqual(len(paragraphs), 1)
                sentences = paragraphs[0]["sentences"]
                self.assertEqual(len(sentences), 2)
                self.assertEqual(" ".join(s["text"] for s in sentences), text)
                self.assertIn(expected_word, [f["word"] for f in frequencies])

    def test_missing_model_reports_setup_command_without_english_fallback(
        self,
    ) -> None:
        service = preprocessing_service.PreprocessingService()
        with mock.patch.object(
            preprocessing_service.spacy, "load", side_effect=OSError("missing")
        ) as load:
            with self.assertRaisesRegex(
                preprocessing_service.MissingLanguageModelError,
                r"de_core_news_sm.*npm run bootstrap",
            ):
                service.process_text("Der Hund läuft.", "German")
        load.assert_called_once_with(
            "de_core_news_sm", disable=["ner", "parser"]
        )


if __name__ == "__main__":
    unittest.main()
