"""Unit tests for authentication, JWT validation, and owner identity resolution."""

from datetime import timedelta
import pathlib
import sys
import unittest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from fastapi.testclient import TestClient

from app import create_app
from core.auth import DEFAULT_OWNER_ID, create_access_token
from core.settings import settings


class TestAuthentication(unittest.TestCase):
    """Test suite for authentication and token validation."""

    def setUp(self):
        self.original_auth_mode = settings.auth_mode
        self.original_secret = settings.jwt_secret
        self.client = self.enterContext(TestClient(create_app()))

    def tearDown(self):
        settings.auth_mode = self.original_auth_mode
        settings.jwt_secret = self.original_secret

    def test_local_mode_default_owner(self):
        """In local mode, requests without headers default to DEFAULT_OWNER_ID."""
        settings.auth_mode = "local"
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["owner_id"], DEFAULT_OWNER_ID)
        self.assertEqual(data["auth_mode"], "local")
        self.assertFalse(data["authenticated"])

    def test_local_mode_header_override(self):
        """In local mode, X-Owner-Id header overrides the default owner."""
        settings.auth_mode = "local"
        response = self.client.get("/auth/me", headers={"X-Owner-Id": "user_override_1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["owner_id"], "user_override_1")
        self.assertTrue(data["authenticated"])

    def test_jwt_bearer_token_resolution(self):
        """Valid JWT token is parsed and its subject is extracted as owner_id."""
        settings.auth_mode = "local"
        token = create_access_token(subject="jwt_user_99")
        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["owner_id"], "jwt_user_99")
        self.assertTrue(data["authenticated"])

    def test_malformed_authorization_header(self):
        """Malformed Authorization header returns HTTP 401."""
        response = self.client.get("/auth/me", headers={"Authorization": "Basic 12345"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid Authorization header format", response.json()["detail"])

        response_empty = self.client.get("/auth/me", headers={"Authorization": "Bearer"})
        self.assertEqual(response_empty.status_code, 401)

    def test_expired_token_rejection(self):
        """Expired JWT token returns HTTP 401 with appropriate message."""
        expired_token = create_access_token(
            subject="expired_user",
            expires_delta=timedelta(seconds=-60),
        )
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"].lower())

    def test_invalid_signature_rejection(self):
        """Token signed with wrong secret is rejected with HTTP 401."""
        invalid_token = create_access_token(
            subject="impostor",
            secret="completely-wrong-secret-key-32-chars-long",
        )
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("invalid", response.json()["detail"].lower())

    def test_strict_jwt_mode_enforcement(self):
        """When AUTH_MODE='jwt', unauthenticated requests are strictly rejected."""
        settings.auth_mode = "jwt"

        # Missing token rejected
        res_missing = self.client.get("/auth/me")
        self.assertEqual(res_missing.status_code, 401)
        self.assertIn("Missing required Authorization bearer token", res_missing.json()["detail"])

        # X-Owner-Id without token rejected in jwt mode
        res_header = self.client.get("/auth/me", headers={"X-Owner-Id": "sneak_in"})
        self.assertEqual(res_header.status_code, 401)

        # Valid token accepted
        valid_token = create_access_token(subject="strict_user_42")
        res_valid = self.client.get("/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(res_valid.json()["owner_id"], "strict_user_42")
        self.assertEqual(res_valid.json()["auth_mode"], "jwt")
        self.assertTrue(res_valid.json()["authenticated"])

    def test_texts_endpoint_enforces_jwt_in_strict_mode(self):
        """Standard API routes enforce JWT token when AUTH_MODE='jwt'."""
        settings.auth_mode = "jwt"

        # Unauthenticated request to /texts rejected
        res_unauth = self.client.get("/texts")
        self.assertEqual(res_unauth.status_code, 401)

        # Authenticated request to /texts accepted
        valid_token = create_access_token(subject="library_user_7")
        res_auth = self.client.get("/texts", headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(res_auth.status_code, 200)
        self.assertIn("data", res_auth.json())


if __name__ == "__main__":
    unittest.main()
