"""Unit and integration tests for structured logging, privacy redaction, correlation IDs, and metrics."""

import json
import logging
import pathlib
import sys
import unittest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from fastapi.testclient import TestClient

from app import create_app
from core.logging import (
    JSONFormatter,
    RedactionFilter,
    current_owner_id,
    current_request_id,
    redact_sensitive_string,
)


class TestLoggingTelemetry(unittest.TestCase):
    """Test suite for structured logging, telemetry, and automated redaction policy."""

    def setUp(self):
        self.client = TestClient(create_app())
        self.formatter = JSONFormatter()
        self.redaction_filter = RedactionFilter()

    def test_json_formatter_valid_schema(self):
        """JSONFormatter outputs single-line valid JSON with standard metadata."""
        record = logging.LogRecord(
            name="typeandlearn.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=30,
            msg="Processing test event: %s",
            args=("success",),
            exc_info=None,
        )
        output = self.formatter.format(record)
        data = json.loads(output)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "typeandlearn.test")
        self.assertEqual(data["message"], "Processing test event: success")
        self.assertIn("timestamp", data)
        self.assertIn("environment", data)
        self.assertIn("service", data)

    def test_correlation_id_context_injection(self):
        """JSONFormatter enriches logs with request_id and owner_id from context variables."""
        token_req = current_request_id.set("req_test_abc123")
        token_owner = current_owner_id.set("owner_test_456")

        try:
            record = logging.LogRecord(
                name="typeandlearn.test",
                level=logging.INFO,
                pathname=__file__,
                lineno=50,
                msg="Contextual event",
                args=(),
                exc_info=None,
            )
            output = self.formatter.format(record)
            data = json.loads(output)

            self.assertEqual(data.get("request_id"), "req_test_abc123")
            self.assertEqual(data.get("owner_id"), "owner_test_456")
        finally:
            current_request_id.reset(token_req)
            current_owner_id.reset(token_owner)

    def test_redaction_scrubs_jwt_and_provider_keys(self):
        """Redaction filter and string scrubber strip JWTs and provider API keys."""
        sample_msg = (
            "Auth failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.fake_signature "
            "with groq_key=gsk_1234567890abcdef12345678 and deepseek=sk-1234567890abcdef12345678"
        )
        scrubbed = redact_sensitive_string(sample_msg)

        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", scrubbed)
        self.assertIn("Bearer [REDACTED_JWT]", scrubbed)
        self.assertNotIn("gsk_1234567890abcdef12345678", scrubbed)
        self.assertIn("[REDACTED_GROQ_KEY]", scrubbed)
        self.assertNotIn("sk-1234567890abcdef12345678", scrubbed)
        self.assertIn("[REDACTED_API_KEY]", scrubbed)

    def test_redaction_scrubs_raw_learning_content_in_extras(self):
        """Redaction filter prevents raw practice sentences and translations from leaking into log records."""
        record = logging.LogRecord(
            name="typeandlearn.practice",
            level=logging.INFO,
            pathname=__file__,
            lineno=80,
            msg="Sentence enriched",
            args=(),
            exc_info=None,
        )
        # Attach raw sensitive texts in extra fields
        record.__dict__["sentence_text"] = "Geheimnisvoller Wald voller Bäume."
        record.__dict__["translation"] = "Mysterious forest full of trees."
        record.__dict__["prompt"] = "Translate the following German text..."

        output = self.formatter.format(record)
        data = json.loads(output)

        # Ensure raw practice texts never appear verbatim
        self.assertNotIn("Geheimnisvoller Wald", output)
        self.assertNotIn("Mysterious forest", output)
        self.assertNotIn("Translate the following", output)

        # Ensure sanitized content hashes and lengths are recorded instead
        self.assertTrue(str(data["sentence_text"]).startswith("[REDACTED_CONTENT: sha256="))
        self.assertTrue(str(data["translation"]).startswith("[REDACTED_CONTENT: sha256="))

    def test_correlation_id_middleware_header_propagation(self):
        """Inbound X-Request-ID header is propagated through middleware to response."""
        # 1. Custom incoming request ID
        res1 = self.client.get("/healthz", headers={"X-Request-ID": "custom-req-id-123"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.headers.get("x-request-id"), "custom-req-id-123")

        # 2. Missing incoming ID generates a new one
        res2 = self.client.get("/healthz")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.headers.get("x-request-id", "").startswith("req_"))

    def test_metrics_endpoint_returns_prometheus_format(self):
        """GET /metrics returns Prometheus-formatted text metrics."""
        # Trigger an API call so metrics has request counts
        self.client.get("/healthz")

        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/plain", res.headers.get("content-type", ""))

        content = res.text
        self.assertIn("typeandlearn_http_requests_total", content)
        self.assertIn("typeandlearn_database_connected 1", content)
        self.assertIn("typeandlearn_app_info", content)


if __name__ == "__main__":
    unittest.main()
