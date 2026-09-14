"""Unit and integration tests for GDPR/CCPA data export and right to erasure."""

import pathlib
import sys
import unittest
import uuid

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from fastapi.testclient import TestClient

from app import create_app
from app_state import (
    analytics_repository,
    cache_repository,
    text_repository,
)
from models.texts import SentenceRecord, TextRecord
from schemas.analytics import PracticeSessionCreate


class TestUserPrivacy(unittest.TestCase):
    """Test suite for GDPR Article 20 data export and Article 17 right to erasure."""

    def setUp(self):
        self.client = self.enterContext(TestClient(create_app()))
        self.owner_a = f"privacy_a_{uuid.uuid4().hex[:8]}"
        self.owner_b = f"privacy_b_{uuid.uuid4().hex[:8]}"

        # Setup data for owner_a
        self.text_a = text_repository.save_text(
            TextRecord(
                title="Privacy Test Text A",
                language="German",
                owner_id=self.owner_a,
            )
        )
        assert self.text_a.id is not None
        text_id = self.text_a.id

        text_repository.save_sentences([
            SentenceRecord(
                owner_id=self.owner_a,
                text_id=text_id,
                paragraph_index=0,
                sentence_index=0,
                original_text="Guten Tag.",
                translation="Good day.",
            )
        ])

        # Practice session & weak words for owner_a
        analytics_repository.record_session(
            owner_id=self.owner_a,
            create_data=PracticeSessionCreate(
                text_id=text_id,
                sentence_index=0,
                sentence_text="Guten Tag.",
                net_wpm=50.0,
                raw_wpm=52.0,
                accuracy=95.0,
                active_seconds=8.0,
                mistake_count=1,
                mistaken_words=["Tag"],
            ),
        )

        # Token usage for owner_a
        cache_repository.record_usage(
            owner_id=self.owner_a,
            provider="groq",
            model="llama-3.3-70b",
            prompt_tokens=100,
            completion_tokens=25,
            total_tokens=125,
            estimated_cost_usd=0.0001,
        )

        # Setup data for owner_b to test non-interference
        self.text_b = text_repository.save_text(
            TextRecord(
                title="Privacy Test Text B",
                language="French",
                owner_id=self.owner_b,
            )
        )

    def test_export_user_data_contains_all_entities(self):
        """GET /user/export returns machine-readable JSON archive of all owned data."""
        res = self.client.get(
            "/user/export",
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/json")
        self.assertIn(f"typeandlearn-export-{self.owner_a}.json", res.headers["content-disposition"])

        payload = res.json()
        self.assertEqual(payload["export_metadata"]["owner_id"], self.owner_a)
        self.assertEqual(payload["export_metadata"]["entity_counts"]["texts"], 1)
        self.assertEqual(payload["export_metadata"]["entity_counts"]["sentences"], 1)
        self.assertEqual(payload["export_metadata"]["entity_counts"]["practice_sessions"], 1)
        self.assertEqual(payload["export_metadata"]["entity_counts"]["weak_words"], 1)
        self.assertEqual(payload["export_metadata"]["entity_counts"]["token_usage_records"], 1)

        self.assertEqual(payload["texts"][0]["title"], "Privacy Test Text A")
        self.assertEqual(payload["weak_words"][0]["word"], "Tag")

    def test_delete_user_account_purges_all_records_safely(self):
        """DELETE /user/account purges all owned records without affecting other owners."""
        # 1. Delete Owner A
        del_res = self.client.delete(
            "/user/account",
            headers={"X-Owner-Id": self.owner_a},
        )
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "deleted")
        self.assertEqual(del_res.json()["owner_id"], self.owner_a)

        # 2. Verify Owner A has zero records left
        export_a = self.client.get(
            "/user/export",
            headers={"X-Owner-Id": self.owner_a},
        ).json()
        counts_a = export_a["export_metadata"]["entity_counts"]
        for entity, count in counts_a.items():
            self.assertEqual(count, 0, f"Expected 0 for {entity} after erasure")

        # 3. Verify Owner B was completely untouched
        export_b = self.client.get(
            "/user/export",
            headers={"X-Owner-Id": self.owner_b},
        ).json()
        self.assertEqual(export_b["export_metadata"]["entity_counts"]["texts"], 1)
        self.assertEqual(export_b["texts"][0]["title"], "Privacy Test Text B")


if __name__ == "__main__":
    unittest.main()
