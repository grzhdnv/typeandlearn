"""Exercise real SDK serialization against fake HTTP, without provider credentials."""

import asyncio
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import httpx
import sqlmodel
from pydantic_ai.exceptions import ModelHTTPError
from sqlmodel import Session, select

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2] / "apps/backend"))

from core.settings import Settings
from models.cache import TokenUsageRecord
from models.providers import ProviderCallRecord
from services.llm_service import LlmNotConfiguredError, LlmService, _can_create_model, should_fallback
from services.provider_governor import ProviderGovernor


class LlmProviderFallbackTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {"GROQ_API_KEY": "fake", "DEEPSEEK_API_KEY": "fake"}, clear=True))
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.engine = sqlmodel.create_engine(f"sqlite:///{directory}/llm.sqlite", connect_args={"check_same_thread": False})
        sqlmodel.SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.cfg = Settings(groq_max_wait_seconds=0, daily_token_limit=1_000_000)
        self.governor = ProviderGovernor(self.engine, self.cfg)
        self.requests = []

    def service(self, handler):
        service = LlmService("apps/backend/prompts/translate_sentence.md", "apps/backend/prompts/generate_practice.md",
                             "groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-120b", ["deepseek:deepseek-flash"],
                             governor=self.governor, transport=httpx.MockTransport(handler))
        self.addCleanup(lambda: asyncio.run(service.aclose()))
        return service

    @staticmethod
    def success(request, invalid=False):
        body = json.loads(request.content)
        schema = body.get("response_format", {}).get("json_schema", {}).get("schema")
        tool = (body.get("tools") or [{}])[0].get("function", {})
        properties = (schema or tool.get("parameters", {})).get("properties", {})
        if "title" in properties:
            output = {"title": "Garden", "difficulty_level": "A1", "language": "German", "author": None, "category": None}
        elif "words" in properties:
            output = {"words": [{"word": "Hund", "count": 2}]}
        elif "sentences" in properties:
            output = {"sentences": [{"sentence": "Der Hund läuft.", "translation": "The dog runs.", "translation_hints": []}] * 5}
        else:
            output = {"translation": 42 if invalid else "The dog runs.", "translation_hints": []}
        message = {"role": "assistant", "content": json.dumps(output)}
        if tool:
            message = {"role": "assistant", "content": None, "tool_calls": [{"id": "call_test", "type": "function", "function": {"name": tool["name"], "arguments": json.dumps(output)}}]}
        model = "deepseek-flash-actual" if request.url.host == "api.deepseek.com" else body["model"]
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 1, "model": model,
                                       "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool else "stop"}],
                                       "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}})

    def test_transient_failover_records_actual_provider_and_shared_cooldown(self):
        def handler(request):
            self.requests.append(request)
            if request.url.host == "api.groq.com":
                return httpx.Response(429, headers={"retry-after": "60"}, json={"error": {"message": "quota"}})
            self.assertEqual(json.loads(request.content)["thinking"], {"type": "disabled"})
            return self.success(request)
        service = self.service(handler)
        for _ in range(2):
            result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft.", owner_id="reader"))
            self.assertEqual(getattr(result, "provider"), "deepseek")
        self.assertEqual([request.url.host for request in self.requests], ["api.groq.com", "api.deepseek.com", "api.deepseek.com"])
        with Session(self.engine) as session:
            usage = session.exec(select(TokenUsageRecord)).all()
            self.assertEqual(len(usage), 2)
            self.assertTrue(all(row.provider == "deepseek" and row.model == "deepseek-flash-actual" and row.owner_id == "reader" for row in usage))
            self.assertTrue(all(row.estimated_cost_usd > 0 for row in usage))

    def test_permanent_errors_do_not_call_paid_fallback_or_retry(self):
        for status in (400, 401, 403, 404, 422):
            with self.subTest(status=status):
                self.requests.clear()
                def handler(request):
                    self.requests.append(request)
                    return httpx.Response(status, json={"error": {"message": "invalid configuration"}})
                service = self.service(handler)
                with self.assertRaises(ModelHTTPError) as error:
                    service.extract_metadata("Der Hund läuft.")
                self.assertEqual(error.exception.status_code, status)
                self.assertEqual(len(self.requests), 1)
                self.assertEqual(self.requests[0].url.host, "api.groq.com")

    def test_all_task_types_are_accounted_and_groq_uses_strict_schema(self):
        def handler(request):
            self.requests.append(request)
            body = json.loads(request.content)
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            self.assertEqual(body["reasoning_effort"], "low")
            return self.success(request)
        service = self.service(handler)
        service.extract_metadata("Der Hund läuft.", owner_id="reader")
        service.filter_meaningful_words([{"word": "Hund", "count": 2}], "German", owner_id="reader")
        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft.", owner_id="reader"))
        asyncio.run(service.generate_practice_sentences_async(["Hund"], owner_id="reader"))
        with Session(self.engine) as session:
            calls = session.exec(select(ProviderCallRecord)).all()
            self.assertEqual({row.task for row in calls}, {"metadata", "filter", "translation", "practice"})
            self.assertEqual(len(session.exec(select(TokenUsageRecord)).all()), 4)
            self.assertTrue(all(row.owner_id == "reader" and row.status == "succeeded" for row in calls))

    def test_qwen_native_schema_profile_and_reasoning_setting(self):
        self.cfg.model_name = self.cfg.structured_model_name = "groq:qwen/qwen3.8-27b"
        def handler(request):
            body = json.loads(request.content)
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            self.assertEqual(body["reasoning_effort"], "none")
            schema = body["response_format"]["json_schema"]["schema"]
            self.assertIs(schema["additionalProperties"], False)
            self.assertIs(schema["$defs"]["HintGroup"]["additionalProperties"], False)
            return self.success(request)
        service = LlmService("apps/backend/prompts/translate_sentence.md", "apps/backend/prompts/generate_practice.md",
                             self.cfg.model_name, self.cfg.structured_model_name, [], governor=self.governor,
                             transport=httpx.MockTransport(handler))
        self.addCleanup(lambda: asyncio.run(service.aclose()))
        asyncio.run(service.translate_sentence_async("Test", "", "Bonjour.", source_language="French"))

    def test_validation_repair_is_bounded_and_each_response_accounted(self):
        def handler(request):
            self.requests.append(request)
            return self.success(request, invalid=len(self.requests) == 1)
        service = self.service(handler)
        result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(result.translation, "The dog runs.")
        self.assertEqual(len(self.requests), 2)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(TokenUsageRecord)).all()), 2)

    def test_exhausted_fallback_budget_blocks_network_request(self):
        self.cfg.deepseek_daily_usd = 0
        def handler(request):
            self.requests.append(request)
            return httpx.Response(503, json={"error": {"message": "unavailable"}})
        service = self.service(handler)
        with self.assertRaises(ModelHTTPError) as error:
            asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(error.exception.status_code, 402)
        self.assertEqual(len(self.requests), 1)

    def test_timeout_falls_back_once(self):
        def handler(request):
            self.requests.append(request)
            if request.url.host == "api.groq.com":
                raise httpx.ReadTimeout("timeout", request=request)
            return self.success(request)
        service = self.service(handler)
        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(len(self.requests), 2)

    def test_offline_and_configuration_checks(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_can_create_model("groq:openai/gpt-oss-120b"))
            service = self.service(lambda request: self.fail("offline service sent HTTP"))
            self.assertFalse(service.is_configured)
            with self.assertRaises(LlmNotConfiguredError):
                service.extract_metadata("Test")
        with self.assertRaises(ValueError):
            _can_create_model("typo:some-model")
        self.assertFalse(should_fallback(ValueError("bad schema")))

    def openrouter_service(self, handler, model="nvidia/nemotron-3-super-120b-a12b:free", pricing=None):
        os.environ["OPENROUTER_API_KEY"] = "fake"
        def wrapped(request):
            if request.method == "GET":
                self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/models")
                self.assertNotIn("authorization", request.headers)
                return httpx.Response(200, json={"data": [{"id": model,
                    "pricing": pricing if pricing is not None else {"prompt": "0", "completion": "0"},
                    "supported_parameters": ["structured_outputs", "response_format", "tools", "tool_choice", "reasoning"]}]})
            self.requests.append(request)
            return handler(request)
        service = LlmService("apps/backend/prompts/translate_sentence.md", "apps/backend/prompts/generate_practice.md",
                             f"openrouter:{model}", f"openrouter:{model}", [], governor=self.governor,
                             transport=httpx.MockTransport(wrapped))
        self.addCleanup(lambda: asyncio.run(service.aclose()))
        return service

    def test_openrouter_free_serialization_all_tasks_and_actual_model(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(request.url.host, "openrouter.ai")
            self.assertEqual(body["provider"], {"allow_fallbacks": False, "require_parameters": True,
                                              "max_price": {"prompt": 0, "completion": 0, "request": 0}})
            self.assertNotIn("models", body)
            self.assertEqual(body["reasoning"], {"enabled": False})
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            response = self.success(request)
            data = response.json()
            data["model"] = "actual-model-version"
            data["usage"]["cost"] = 0
            return httpx.Response(200, json=data)
        self.cfg.deepseek_daily_usd = self.cfg.deepseek_monthly_usd = 0
        service = self.openrouter_service(handler)
        service.extract_metadata("Der Hund läuft.")
        service.filter_meaningful_words([{"word": "Hund", "count": 2}], "German")
        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        asyncio.run(service.generate_practice_sentences_async(["Hund"]))
        with Session(self.engine) as session:
            calls = session.exec(select(ProviderCallRecord)).all()
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(c.provider == "openrouter" and c.cost_microusd == 0 and c.response_model == "actual-model-version" for c in calls))

    def test_openrouter_ultra_uses_typed_tool_output(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertIn("tools", body)
            self.assertNotIn("response_format", body)
            return self.success(request)
        service = self.openrouter_service(handler, "nvidia/nemotron-3-ultra-550b-a55b:free")
        service.extract_metadata("Test")

    def test_openrouter_catalog_price_blocks_before_inference(self):
        for pricing in ({"prompt": "0.001", "completion": "0"}, {"prompt": "0"},
                        {"prompt": "0", "completion": "0", "request": "1"}):
            service = self.openrouter_service(lambda request: self.fail("Paid inference attempted"), pricing=pricing)
            with self.assertRaises(ModelHTTPError) as error:
                service.extract_metadata("Test")
            self.assertEqual(error.exception.status_code, 400)
        with self.assertRaises(ValueError):
            _can_create_model("openrouter:nvidia/paid-model")
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ProviderCallRecord)).all()), 0)

    def test_openrouter_permanent_errors_no_retry_or_fallback(self):
        for code in (400, 401, 402, 403, 404, 422):
            self.requests.clear()
            service = self.openrouter_service(lambda request: httpx.Response(code, json={"error": {"message": "blocked"}}))
            with self.assertRaises(ModelHTTPError):
                service.extract_metadata("Test")
            self.assertEqual(len(self.requests), 1)

    def test_openrouter_repair_attempt_is_reserved_separately(self):
        service = self.openrouter_service(lambda request: self.success(request, invalid=len(self.requests) == 1))
        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(len(self.requests), 2)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ProviderCallRecord)).all()), 2)

    def test_openrouter_429_blocks_following_dispatch(self):
        self.cfg.openrouter_max_wait_seconds = 0
        service = self.openrouter_service(lambda request: httpx.Response(429, headers={"retry-after": "60"}, json={"error": {"message": "quota"}}))
        for _ in range(2):
            with self.assertRaises(ModelHTTPError):
                service.extract_metadata("Test")
        self.assertEqual(len(self.requests), 1)
