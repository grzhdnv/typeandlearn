"""Exercise real SDK serialization against fake HTTP, without provider credentials."""

import asyncio
import json
import os
import re
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
            output = {"sentences": [{"sentence": "Der Hund läuft.", "translation": "The dog runs.", "translation_hints": [{"words": ["Der", "Hund", "läuft"], "hint": "The dog runs"}]}] * 5}
        else:
            source = next((str(m.get("content", "")).split("TARGET_SENTENCE: ", 1)[1].splitlines()[0] for m in body["messages"] if m.get("role") == "user" and "TARGET_SENTENCE: " in str(m.get("content", ""))), "Der Hund läuft.")
            words = [re.sub(r"[.,!?]+$", "", w) for w in source.split()]
            output = {"translation": 42 if invalid else "The dog runs.", "translation_hints": [{"words": words, "hint": "Test meaning"}]}
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
            output_limit = body.get("max_completion_tokens", body.get("max_tokens"))
            self.assertEqual(output_limit, self.cfg.llm_practice_max_output_tokens if "sentences" in body["response_format"]["json_schema"]["schema"]["properties"] else self.cfg.llm_max_output_tokens)
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
                    "reasoning": {"mandatory": model.startswith("minimax/"), "supported_efforts": ["high", "low"]},
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

    def test_minimax_mandatory_reasoning_uses_low_effort_json_for_all_tasks(self):
        outputs = [
            {"title": "Test", "difficulty_level": "A1", "language": "German"},
            {"words": [{"word": "Hund", "count": 2}]},
            {"translation": "The dog runs.", "translation_hints": [{"words": ["Der", "Hund", "läuft"], "hint": "The dog runs"}]},
            {"sentences": [{"sentence": "Der Hund läuft.", "translation": "The dog runs.", "translation_hints": [{"words": ["Der", "Hund", "läuft"], "hint": "The dog runs"}]}] * 5},
        ]
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(body["reasoning"], {"effort": "low"})
            self.assertNotIn("tools", body)
            self.assertNotIn("tool_choice", body)
            self.assertEqual(body["response_format"], {"type": "json_object"})
            self.assertFalse(body["provider"]["allow_fallbacks"])
            response = self.success(request).json()
            response["choices"][0]["message"] = {"role": "assistant", "content": json.dumps(outputs[len(self.requests) - 1])}
            return httpx.Response(200, json=response)
        service = self.openrouter_service(handler, "minimax/minimax-m3.1-flash:free")
        service.extract_metadata("Test")
        service.filter_meaningful_words([{"word": "Hund", "count": 2}], "German")
        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        asyncio.run(service.generate_practice_sentences_async(["Hund"]))
        self.assertEqual(len(self.requests), 4)

    @staticmethod
    def missing_hints(request):
        data = LlmProviderFallbackTests.success(request).json()
        message = data["choices"][0]["message"]
        if message.get("tool_calls"):
            function = message["tool_calls"][0]["function"]
            output = json.loads(function["arguments"])
            output["translation_hints"] = []
            function["arguments"] = json.dumps(output)
        else:
            output = json.loads(message["content"])
            output["translation_hints"] = []
            message["content"] = json.dumps(output)
        return httpx.Response(200, json=data)

    def test_hint_coverage_repair_is_bounded_and_accounted(self):
        def handler(request):
            self.requests.append(request)
            return self.missing_hints(request) if len(self.requests) == 1 else self.success(request)
        service = self.service(handler)
        result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(result.translation_hints[0].words, ["Der", "Hund", "läuft"])
        self.assertEqual(len(self.requests), 2)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ProviderCallRecord)).all()), 2)

    def chain(self, openrouter_handler):
        os.environ["OPENROUTER_API_KEY"] = "fake"
        def handler(request):
            if request.method == "GET":
                return httpx.Response(200, json={"data": [{"id": "minimax/minimax-m3.1-flash:free",
                    "pricing": {"prompt": "0", "completion": "0"},
                    "reasoning": {"mandatory": True, "supported_efforts": ["low"]},
                    "supported_parameters": ["response_format", "reasoning"]}]})
            self.requests.append(request)
            if request.url.host == "api.groq.com":
                return httpx.Response(503, json={"error": {"message": "unavailable"}})
            if request.url.host == "openrouter.ai":
                return openrouter_handler(request)
            return self.success(request)
        service = LlmService("apps/backend/prompts/translate_sentence.md", "apps/backend/prompts/generate_practice.md",
                             "groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-120b",
                             ["openrouter:minimax/minimax-m3.1-flash:free", "deepseek:deepseek-flash"],
                             governor=self.governor, transport=httpx.MockTransport(handler))
        self.addCleanup(lambda: asyncio.run(service.aclose()))
        return service

    def test_three_provider_chain_handles_schema_exhaustion_and_paid_caps(self):
        for paid_budget in (0, .5):
            with self.subTest(paid_budget=paid_budget):
                self.requests.clear()
                self.cfg.deepseek_daily_usd = paid_budget
                service = self.chain(self.missing_hints)
                if paid_budget:
                    result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
                    self.assertEqual(getattr(result, "provider"), "deepseek")
                else:
                    with self.assertRaises(ModelHTTPError) as error:
                        asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
                    self.assertEqual(error.exception.status_code, 402)
                hosts = [r.url.host for r in self.requests]
                self.assertEqual(hosts.count("openrouter.ai"), 2)
                self.assertEqual(hosts.count("api.deepseek.com"), int(bool(paid_budget)))

    def test_three_provider_chain_falls_back_on_openrouter_quota(self):
        service = self.chain(lambda request: httpx.Response(429, headers={"retry-after": "60"}, json={"error": {"message": "quota"}}))
        result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(getattr(result, "provider"), "deepseek")
        self.assertEqual([r.url.host for r in self.requests], ["api.groq.com", "openrouter.ai", "api.deepseek.com"])

    def test_three_provider_chain_does_not_spend_after_bad_credentials(self):
        service = self.chain(lambda request: httpx.Response(401, json={"error": {"message": "bad key"}}))
        with self.assertRaises(ModelHTTPError) as error:
            asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(error.exception.status_code, 401)
        self.assertNotIn("api.deepseek.com", [r.url.host for r in self.requests])

    def test_three_provider_chain_stops_at_valid_free_response(self):
        service = self.chain(self.success)
        result = asyncio.run(service.translate_sentence_async("Test", "", "Der Hund läuft."))
        self.assertEqual(getattr(result, "provider"), "openrouter")
        self.assertEqual([r.url.host for r in self.requests], ["api.groq.com", "openrouter.ai"])
        with Session(self.engine) as session:
            usage = session.exec(select(TokenUsageRecord)).all()
            self.assertEqual(len(usage), 1)
            self.assertEqual(usage[0].provider, "openrouter")
            self.assertEqual(usage[0].estimated_cost_usd, 0)
