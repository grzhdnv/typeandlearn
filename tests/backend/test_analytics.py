"""Unit and integration tests for practice sessions and learning analytics."""

import pathlib
import sys
import unittest
import uuid

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from fastapi.testclient import TestClient

from app import create_app
from app_state import text_repository
from models.texts import TextRecord


class TestAnalytics(unittest.TestCase):
    """Test suite for analytics recording, summary computation, and weak word tracking."""

    def setUp(self):
        self.client = self.enterContext(TestClient(create_app()))
        self.owner_a = f"owner_a_{uuid.uuid4().hex[:8]}"
        self.owner_b = f"owner_b_{uuid.uuid4().hex[:8]}"

        # Create a text for owner_a
        self.text_a = text_repository.save_text(
            TextRecord(
                title="German Practice Story",
                language="German",
                author="Hans",
                category="Animals",
                owner_id=self.owner_a,
            )
        )

    def test_record_session_and_update_weak_words(self):
        """Posting a practice session persists drill metrics and upserts weak words."""
        payload = {
            "text_id": self.text_a.id,
            "sentence_index": 0,
            "sentence_text": "Der Hund läuft im Garten.",
            "target_type": "original",
            "net_wpm": 45.2,
            "raw_wpm": 48.0,
            "accuracy": 94.5,
            "active_seconds": 12.4,
            "mistake_count": 2,
            "mistakes_detail": [
                {"expected": "Hund", "typed": "Hundd"},
                {"expected": "Garten", "typed": "Gartenn"},
            ],
            "mistaken_words": ["Hund", "Garten"],
        }

        # 1. Record session
        res = self.client.post(
            "/analytics/sessions",
            json=payload,
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["owner_id"], self.owner_a)
        self.assertEqual(data["net_wpm"], 45.2)
        self.assertEqual(data["mistake_count"], 2)

        # 2. Verify weak words
        ww_res = self.client.get(
            "/analytics/weak-words",
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(ww_res.status_code, 200)
        weak_words = ww_res.json()
        self.assertEqual(len(weak_words), 2)
        words = {w["word"]: w["mistake_count"] for w in weak_words}
        self.assertEqual(words.get("Hund"), 1)
        self.assertEqual(words.get("Garten"), 1)

        # 3. Record second session with another mistake on "Hund"
        payload_2 = {
            "text_id": self.text_a.id,
            "sentence_index": 1,
            "sentence_text": "Die Katze schläft.",
            "target_type": "original",
            "net_wpm": 55.0,
            "raw_wpm": 56.0,
            "accuracy": 98.0,
            "active_seconds": 10.0,
            "mistake_count": 1,
            "mistaken_words": ["Hund"],
        }
        res_2 = self.client.post(
            "/analytics/sessions",
            json=payload_2,
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(res_2.status_code, 201)

        # Verify mistake count incremented for "Hund"
        ww_res_2 = self.client.get(
            "/analytics/weak-words",
            headers={"X-Owner-Id": self.owner_a},
        )
        weak_words_2 = ww_res_2.json()
        words_2 = {w["word"]: w["mistake_count"] for w in weak_words_2}
        self.assertEqual(words_2.get("Hund"), 2)

    def test_analytics_summary_and_trend(self):
        """Summary aggregates lifetime KPIs and recent chronological trend points."""
        # Record two drills
        for i, (wpm, acc, secs, mistakes) in enumerate([
            (40.0, 90.0, 15.0, 3),
            (60.0, 100.0, 10.0, 0),
        ]):
            self.client.post(
                "/analytics/sessions",
                json={
                    "text_id": self.text_a.id,
                    "sentence_index": i,
                    "sentence_text": f"Sentence {i}",
                    "net_wpm": wpm,
                    "raw_wpm": wpm,
                    "accuracy": acc,
                    "active_seconds": secs,
                    "mistake_count": mistakes,
                },
                headers={"X-Owner-Id": self.owner_a},
            )

        # Query summary
        summary_res = self.client.get(
            "/analytics/summary",
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(summary_res.status_code, 200)
        summary = summary_res.json()

        self.assertEqual(summary["total_drills"], 2)
        self.assertEqual(summary["total_practice_seconds"], 25.0)
        self.assertEqual(summary["avg_net_wpm"], 50.0)
        self.assertEqual(summary["peak_net_wpm"], 60.0)
        self.assertEqual(summary["avg_accuracy"], 95.0)
        self.assertEqual(summary["total_mistakes"], 3)
        self.assertEqual(len(summary["recent_trend"]), 2)
        self.assertEqual(summary["recent_trend"][0]["net_wpm"], 40.0)
        self.assertEqual(summary["recent_trend"][1]["net_wpm"], 60.0)

    def test_multi_tenant_analytics_isolation(self):
        """Owner B cannot access or view analytics belonging to Owner A."""
        # Owner A completes a drill
        self.client.post(
            "/analytics/sessions",
            json={
                "text_id": self.text_a.id,
                "sentence_index": 0,
                "sentence_text": "Sample text",
                "net_wpm": 75.0,
                "raw_wpm": 75.0,
                "accuracy": 100.0,
                "active_seconds": 8.0,
                "mistake_count": 0,
                "mistaken_words": ["SecretWord"],
            },
            headers={"X-Owner-Id": self.owner_a},
        )

        # Owner B queries summary -> clean zero baseline
        summary_b = self.client.get(
            "/analytics/summary",
            headers={"X-Owner-Id": self.owner_b},
        ).json()
        self.assertEqual(summary_b["total_drills"], 0)
        self.assertEqual(summary_b["total_practice_seconds"], 0.0)
        self.assertEqual(summary_b["recent_trend"], [])

        # Owner B queries weak words -> empty list
        weak_words_b = self.client.get(
            "/analytics/weak-words",
            headers={"X-Owner-Id": self.owner_b},
        ).json()
        self.assertEqual(weak_words_b, [])

        # Owner B queries history -> empty list
        history_b = self.client.get(
            "/analytics/history",
            headers={"X-Owner-Id": self.owner_b},
        ).json()
        self.assertEqual(history_b, [])


if __name__ == "__main__":
    unittest.main()
