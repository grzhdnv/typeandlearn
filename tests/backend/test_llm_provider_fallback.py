"""Tests for Groq-first provider routing, fallback chaining, and offline handling."""

import asyncio
import os
import pathlib
import sys
import unittest
from unittest import mock

import httpx
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIChatModel

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from services.llm_service import (
    LlmNotConfiguredError,
    LlmService,
    _build_model_chain,
    _can_create_model,
)


class LlmProviderFallbackTests(unittest.TestCase):
    """Verify Groq-first routing, DeepSeek failover, and offline mode."""

    def setUp(self) -> None:
        self.client = httpx.AsyncClient()
        self.addCleanup(lambda: asyncio.run(self.client.aclose()))

    def test_can_create_model_env_checks(self) -> None:
        """_can_create_model correctly checks provider-specific API keys."""
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_can_create_model("groq:llama-3.3-70b-versatile"))
            self.assertFalse(_can_create_model("deepseek:deepseek-chat"))

        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}, clear=True):
            self.assertTrue(_can_create_model("groq:llama-3.3-70b-versatile"))
            self.assertFalse(_can_create_model("deepseek:deepseek-chat"))

        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "dsk_test"}, clear=True):
            self.assertFalse(_can_create_model("groq:llama-3.3-70b-versatile"))
            self.assertTrue(_can_create_model("deepseek:deepseek-chat"))

    def test_both_keys_build_fallback_model(self) -> None:
        """When both keys are set, FallbackModel is returned with Groq primary and DeepSeek fallback."""
        env = {
            "GROQ_API_KEY": "gsk_test_key",
            "DEEPSEEK_API_KEY": "dsk_test_key",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            model = _build_model_chain(
                "groq:llama-3.3-70b-versatile",
                ["deepseek:deepseek-chat"],
                self.client,
            )
            self.assertIsInstance(model, FallbackModel)
            assert isinstance(model, FallbackModel)
            self.assertIsInstance(model.models[0], GroqModel)
            self.assertIsInstance(model.models[1], OpenAIChatModel)

    def test_only_groq_key_builds_single_groq_model(self) -> None:
        """When only GROQ_API_KEY is present, single GroqModel is returned."""
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_key"}, clear=True):
            model = _build_model_chain(
                "groq:llama-3.3-70b-versatile",
                ["deepseek:deepseek-chat"],
                self.client,
            )
            self.assertIsInstance(model, GroqModel)

    def test_only_deepseek_key_promotes_deepseek(self) -> None:
        """When only DEEPSEEK_API_KEY is present, DeepSeek is promoted to primary."""
        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "dsk_test_key"}, clear=True):
            model = _build_model_chain(
                "groq:llama-3.3-70b-versatile",
                ["deepseek:deepseek-chat"],
                self.client,
            )
            self.assertIsInstance(model, OpenAIChatModel)

    def test_neither_key_raises_not_configured(self) -> None:
        """When neither key is set, _build_model_chain raises LlmNotConfiguredError."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LlmNotConfiguredError):
                _build_model_chain(
                    "groq:llama-3.3-70b-versatile",
                    ["deepseek:deepseek-chat"],
                    self.client,
                )

    def test_llm_service_offline_boot(self) -> None:
        """LlmService initializes cleanly with is_configured=False when uncredentialed."""
        with mock.patch.dict(os.environ, {}, clear=True):
            service = LlmService(
                translation_prompt_path="apps/backend/prompts/translate_sentence.md",
                practice_prompt_path="apps/backend/prompts/generate_practice.md",
                model_name="groq:llama-3.3-70b-versatile",
                structured_model_name="groq:llama-3.3-70b-versatile",
                fallback_models=["deepseek:deepseek-chat"],
            )
            self.assertFalse(service.is_configured)
            with self.assertRaises(LlmNotConfiguredError):
                service.extract_metadata("Sample text")

    def test_fallback_model_delegation_on_error(self) -> None:
        """FallbackModel delegates to secondary provider when primary encounters 429/error."""
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelAPIError
        from pydantic_ai.models.test import TestModel

        call_log = []

        class FailingModel(TestModel):
            async def request(self, *args, **kwargs):
                call_log.append("groq_primary")
                raise ModelAPIError("groq", "HTTP 429 Rate Limit Exceeded")

        class BackupModel(TestModel):
            async def request(self, *args, **kwargs):
                call_log.append("deepseek_fallback")
                return await super().request(*args, **kwargs)

        fallback_model = FallbackModel(FailingModel(), BackupModel())
        agent = Agent(fallback_model)
        result = asyncio.run(agent.run("Test prompt"))
        self.assertEqual(call_log, ["groq_primary", "deepseek_fallback"])
        self.assertIsNotNone(result.output)
