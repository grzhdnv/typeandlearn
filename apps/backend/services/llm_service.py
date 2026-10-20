"""Typed Groq-first tasks with explicit failover and transport-level accounting."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
import json
import logging
import math
import os
import threading
import time
from typing import Any, TypeVar, cast

import httpx
from groq import AsyncGroq, APIConnectionError as GroqConnectionError
from openai import AsyncOpenAI, APIConnectionError as OpenAIConnectionError
from pydantic import BaseModel
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer, OpenAIModelProfile
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.groq import GroqProvider

from core.settings import Settings
from schemas.texts import FilteredWordsResponse, GeneratedMetadata, PracticeSentencesResponse, SentenceTranslation
from services.provider_governor import ProviderBudgetExceeded, ProviderGovernor, QuotaUnavailable

logger = logging.getLogger("typeandlearn.llm")
_owner: ContextVar[str] = ContextVar("provider_owner", default="owner_local_default")
_task: ContextVar[str] = ContextVar("provider_task", default="unknown")
T = TypeVar("T", bound=BaseModel)


def should_fallback(error: Exception) -> bool:
    seen: set[int] = set()
    cause: BaseException | None = error
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, ModelHTTPError):
            return cause.status_code in (408, 429, 500, 502, 503, 504)
        if isinstance(cause, (httpx.TransportError, GroqConnectionError, OpenAIConnectionError)):
            return True
        cause = cause.__cause__
    return False


class _GovernedTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport, governor: ProviderGovernor | None, settings: Settings):
        self.transport, self.governor, self.settings = transport, governor, settings

    async def aclose(self) -> None:
        await self.transport.aclose()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body_bytes = await request.aread()
        body = json.loads(body_bytes)
        hosts = {"api.groq.com": "groq", "api.deepseek.com": "deepseek"}
        provider = hosts[request.url.host]
        model = str(body["model"])
        if len(body_bytes) > self.settings.llm_max_request_bytes:
            return httpx.Response(400, request=request, json={"error": {"message": "LLM request exceeds the configured input size limit"}})
        max_output = int(body.get("max_completion_tokens") or body.get("max_tokens") or self.settings.llm_max_output_tokens)
        input_bound = len(body_bytes) + 512 + 64 * len(body.get("messages", []))
        estimate = math.ceil(len(body_bytes) / 3) + 128
        call_id = None
        if self.governor:
            deadline = time.monotonic() + (self.settings.groq_max_wait_seconds if provider == "groq" else 0)
            while True:
                try:
                    call_id = await asyncio.to_thread(self.governor.reserve, provider, model, _owner.get(), _task.get(), input_bound, estimate, max_output)
                    break
                except QuotaUnavailable as error:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or error.wait_seconds > remaining:
                        return httpx.Response(429, request=request, headers={"retry-after": str(math.ceil(error.wait_seconds))},
                                              json={"error": {"message": "Provider quota is unavailable; try fallback or retry later"}})
                    await asyncio.sleep(min(error.wait_seconds, remaining))
                except ProviderBudgetExceeded as error:
                    return httpx.Response(402, request=request, json={"error": {"message": str(error)}})
        try:
            response = await self.transport.handle_async_request(request)
            await response.aread()
        except BaseException:
            if call_id and self.governor:
                await asyncio.shield(asyncio.to_thread(self.governor.finish, call_id, None))
            raise
        if call_id and self.governor:
            try:
                data = response.json()
            except (ValueError, UnicodeDecodeError):
                data = {}
            await asyncio.to_thread(self.governor.finish, call_id, response.status_code,
                                    data if isinstance(data, dict) else {}, dict(response.headers))
        return response


def _create_model(model_spec: str, client: httpx.AsyncClient, max_tokens: int = 2048) -> Model:
    provider_name, _, model_name = model_spec.partition(":")
    if provider_name == "deepseek":
        sdk = AsyncOpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com", http_client=client, max_retries=0)
        provider = DeepSeekProvider(openai_client=sdk)
        profile = (DeepSeekProvider.model_profile(model_name) or OpenAIModelProfile()).update(OpenAIModelProfile(openai_supports_tool_choice_required=False))
        return OpenAIChatModel(model_name, provider=provider, profile=profile,
                               settings={"max_tokens": max_tokens, "extra_body": {"thinking": {"type": "disabled"}}})
    if provider_name == "groq":
        sdk = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"), http_client=client, max_retries=0)
        # The pinned SDK predates Groq native schemas for Qwen 3.8.
        profile = OpenAIModelProfile(supports_json_schema_output=True, json_schema_transformer=OpenAIJsonSchemaTransformer) if model_name == "qwen/qwen3.8-27b" else None
        return GroqModel(model_name, provider=GroqProvider(groq_client=sdk), profile=profile, settings={
            "max_tokens": max_tokens,
            "extra_body": {"reasoning_effort": "none" if model_name.startswith("qwen/") else "low"},
        })
    raise ValueError(f"Unsupported LLM provider: {provider_name}")


def _can_create_model(model_spec: str) -> bool:
    provider, _, model = model_spec.partition(":")
    if not model or provider not in ("groq", "deepseek"):
        raise ValueError("LLM models must use a groq: or deepseek: prefix")
    return bool(os.getenv("GROQ_API_KEY" if provider == "groq" else "DEEPSEEK_API_KEY"))


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmService:
    def __init__(self, translation_prompt_path: str, practice_prompt_path: str,
                 model_name: str, structured_model_name: str,
                 fallback_models: list[str] | None = None, *, governor: ProviderGovernor | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._model_name, self._structured_model_name = model_name, structured_model_name
        self._fallbacks = fallback_models or []
        self._governor = governor
        self._settings = governor.settings if governor else Settings()
        self._prompts = {
            "translation": self._read_prompt(translation_prompt_path),
            "practice": self._read_prompt(practice_prompt_path),
            "metadata": self._read_prompt("apps/backend/prompts/metadata_prompt.txt"),
            "filter": self._read_prompt("apps/backend/prompts/filter_words_prompt.txt"),
        }
        specs = list(dict.fromkeys([model_name, structured_model_name, *self._fallbacks]))
        available = [spec for spec in specs if _can_create_model(spec)]
        self.is_configured = bool(available)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._loop_lock = threading.Lock()
        self._client: httpx.AsyncClient | None = None
        self._models: dict[str, Model] = {}
        if available:
            self._client = httpx.AsyncClient(timeout=30, transport=_GovernedTransport(transport or httpx.AsyncHTTPTransport(retries=0), governor, self._settings))
            self._models = {spec: _create_model(spec, self._client, self._settings.llm_max_output_tokens) for spec in available}

    @staticmethod
    def _read_prompt(path: str) -> str:
        with open(path, encoding="utf-8") as file:
            return file.read()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def structured_model_name(self) -> str:
        return self._structured_model_name

    @property
    def usage_recorded_at_transport(self) -> bool:
        return self._governor is not None

    def _submit(self, coroutine):
        # Sync API threads and async workers share one provider loop and HTTP pool.
        with self._loop_lock:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="typeandlearn-providers")
                self._thread.start()
            return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def aclose(self) -> None:
        if self._client is not None:
            await asyncio.wrap_future(self._submit(self._client.aclose()))
        if self._loop is not None and self._thread is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            await asyncio.to_thread(self._thread.join)
            self._loop.close()
            self._loop, self._thread = None, None

    async def _execute(self, task: str, prompt: str, output_type: type[T], owner_id: str) -> tuple[T, Any, str]:
        if not self.is_configured:
            raise LlmNotConfiguredError("LLM provider credentials are not configured.")
        owner_token, task_token = _owner.set(owner_id), _task.set(task)
        primary = self._model_name if task == "translation" else self._structured_model_name
        specs = [spec for spec in dict.fromkeys([primary, *self._fallbacks]) if spec in self._models]
        try:
            for index, spec in enumerate(specs):
                output = NativeOutput(output_type, strict=True) if spec.startswith("groq:") and self._models[spec].profile.supports_json_schema_output else output_type
                agent = Agent(self._models[spec], output_type=output, system_prompt=self._prompts[task], retries=1)
                try:
                    result = await agent.run(prompt)
                    return cast(T, result.output), result.usage(), spec
                except Exception as error:
                    if index == len(specs) - 1 or not should_fallback(error):
                        raise
                    logger.warning("Switching provider after transient failure", extra={"model": spec, "status_code": getattr(error, "status_code", None)})
            raise LlmNotConfiguredError("No model is configured for this task.")
        finally:
            _owner.reset(owner_token)
            _task.reset(task_token)

    async def translate_sentence_with_usage_async(self, title: str, context: str, target_sentence: str,
                                                  owner_id: str = "owner_local_default", source_language: str = "German") -> tuple[SentenceTranslation, Any]:
        result, usage, spec = await asyncio.wrap_future(self._submit(self._execute("translation",
            f"LANGUAGE: {source_language}\nTITLE: {title}\nCONTEXT: {context}\nTARGET_SENTENCE: {target_sentence}", SentenceTranslation, owner_id)))
        setattr(result, "provider", spec.split(":", 1)[0])
        setattr(result, "model", spec.split(":", 1)[1])
        return result, usage

    async def translate_sentence_async(self, title: str, context: str, target_sentence: str,
                                       owner_id: str = "owner_local_default", source_language: str = "German") -> SentenceTranslation:
        output, usage = await self.translate_sentence_with_usage_async(title, context, target_sentence, owner_id, source_language)
        setattr(output, "usage", usage)
        return output

    def translate_sentence(self, title: str, context: str, target_sentence: str,
                           owner_id: str = "owner_local_default", source_language: str = "German") -> SentenceTranslation:
        return asyncio.run(self.translate_sentence_async(title, context, target_sentence, owner_id, source_language))

    async def generate_practice_sentences_with_usage_async(self, words: list[str], owner_id: str = "owner_local_default", source_language: str = "German") -> tuple[PracticeSentencesResponse, Any]:
        output, usage, spec = await asyncio.wrap_future(self._submit(self._execute("practice",
            f"LANGUAGE: {source_language}\nWORDS: {json.dumps(words, ensure_ascii=False)}", PracticeSentencesResponse, owner_id)))
        setattr(output, "provider", spec.split(":", 1)[0])
        setattr(output, "model", spec.split(":", 1)[1])
        return output, usage

    async def generate_practice_sentences_async(self, words: list[str], owner_id: str = "owner_local_default", source_language: str = "German") -> PracticeSentencesResponse:
        output, usage = await self.generate_practice_sentences_with_usage_async(words, owner_id, source_language)
        setattr(output, "usage", usage)
        return output

    def generate_practice_sentences(self, words: list[str], owner_id: str = "owner_local_default", source_language: str = "German") -> PracticeSentencesResponse:
        return asyncio.run(self.generate_practice_sentences_async(words, owner_id, source_language))

    def extract_metadata(self, text: str, owner_id: str = "owner_local_default") -> GeneratedMetadata:
        output, _, _ = self._submit(self._execute("metadata", f"TEXT:\n{text[:2000]}", GeneratedMetadata, owner_id)).result()
        return output

    def filter_meaningful_words(self, raw_frequencies: list[dict], language: str,
                                owner_id: str = "owner_local_default") -> FilteredWordsResponse:
        output, _, _ = self._submit(self._execute("filter", f"LANGUAGE: {language}\nRAW_FREQUENCIES: {json.dumps(raw_frequencies, ensure_ascii=False)}", FilteredWordsResponse, owner_id)).result()
        return output
