"""Service for generating structured text data via an LLM provider."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.groq import GroqProvider

from schemas.texts import FilteredWordsResponse
from schemas.texts import GeneratedMetadata
from schemas.texts import PracticeSentencesResponse
from schemas.texts import SentenceTranslation

# Create logs directory if it doesn't exist
os.makedirs("apps/backend/logs", exist_ok=True)

logger = logging.getLogger("typeandlearn.llm")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler("apps/backend/logs/llm.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)


class _HeaderCaptureTransport(httpx.AsyncBaseTransport):
    """Capture provider rate-limit metadata without logging payloads."""

    def __init__(self, transport: httpx.AsyncBaseTransport):
        self._transport = transport

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        response = await self._transport.handle_async_request(request)
        remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
        if remaining_tokens:
            logger.info(
                "Provider rate-limit tokens remaining: %s",
                remaining_tokens,
            )
        return response


def _create_model(model_spec: str, client: httpx.AsyncClient) -> Model:
    """Create a configured Pydantic AI model from a provider-prefixed name."""
    if model_spec.startswith("deepseek:"):
        provider = DeepSeekProvider(http_client=client)
        model_name = model_spec.removeprefix("deepseek:")
        profile = DeepSeekProvider.model_profile(model_name)
        if profile:
            profile = profile.update(
                OpenAIModelProfile(openai_supports_tool_choice_required=False)
            )
        return OpenAIChatModel(model_name, provider=provider, profile=profile)

    provider = GroqProvider(http_client=client)
    model_name = model_spec.removeprefix("groq:")
    return GroqModel(model_name, provider=provider)


def _can_create_model(model_spec: str) -> bool:
    """Check whether required environment variables exist for a given model spec."""
    if model_spec.startswith("deepseek:"):
        return bool(os.getenv("DEEPSEEK_API_KEY"))
    if model_spec.startswith("groq:"):
        return bool(os.getenv("GROQ_API_KEY"))
    return True


def _build_model_chain(
    primary_spec: str,
    fallback_specs: list[str] | None,
    client: httpx.AsyncClient,
) -> Model:
    """Assemble primary and fallback models based on available provider credentials.

    If both Groq and DeepSeek keys exist, Groq is the primary model and DeepSeek is
    the fallback model. If only one exists, that provider is used.
    """
    candidates = [primary_spec] + (fallback_specs or [])
    available_models: list[Model] = []
    seen_specs: set[str] = set()

    for spec in candidates:
        if spec in seen_specs:
            continue
        seen_specs.add(spec)
        if _can_create_model(spec):
            try:
                model = _create_model(spec, client)
                available_models.append(model)
                logger.info("Initialized provider model: %s", spec)
            except Exception as err:
                logger.warning("Failed to initialize model %s: %s", spec, err)

    if not available_models:
        raise LlmNotConfiguredError("No LLM provider credentials configured.")

    if len(available_models) == 1:
        return available_models[0]

    logger.info(
        "Configured primary model (%s) with %d fallback model(s)",
        primary_spec,
        len(available_models) - 1,
    )
    return FallbackModel(
        available_models[0],
        *available_models[1:],
        fallback_on=(ModelAPIError, httpx.HTTPError),
    )


class LlmNotConfiguredError(RuntimeError):
    """Raised when an LLM operation is invoked without configured provider credentials."""

    pass


class LlmService:
    """Generate translations and practice sentences using Pydantic AI."""

    def __init__(
        self,
        translation_prompt_path: str,
        practice_prompt_path: str,
        model_name: str,
        structured_model_name: str,
        fallback_models: list[str] | None = None,
    ) -> None:
        """Configure prompt sources and initialize Pydantic AI agents if keys exist."""
        self._model_name = model_name
        self._structured_model_name = structured_model_name
        self._translation_prompt = self._read_prompt(translation_prompt_path)
        self._practice_prompt = self._read_prompt(practice_prompt_path)
        self.is_configured = False
        self._translation_agent = None
        self._practice_agent = None
        self._metadata_agent = None
        self._filter_agent = None
        self._semaphore = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY_LIMIT", "5")))

        try:
            client = httpx.AsyncClient(
                transport=_HeaderCaptureTransport(httpx.AsyncHTTPTransport())
            )

            self._active_model = _build_model_chain(
                model_name, fallback_models, client
            )
            self._active_structured_model = _build_model_chain(
                structured_model_name, fallback_models, client
            )

            self._translation_agent = Agent(
                self._active_model,
                output_type=SentenceTranslation,
                system_prompt=self._translation_prompt,
                retries=3,
            )

            self._practice_agent = Agent(
                self._active_structured_model,
                output_type=PracticeSentencesResponse,
                system_prompt=self._practice_prompt,
                retries=3,
            )

            metadata_prompt_path = "apps/backend/prompts/metadata_prompt.txt"
            self._metadata_agent = Agent(
                self._active_structured_model,
                output_type=GeneratedMetadata,
                system_prompt=self._read_prompt(metadata_prompt_path),
                retries=3,
            )

            filter_prompt_path = "apps/backend/prompts/filter_words_prompt.txt"
            self._filter_agent = Agent(
                self._active_structured_model,
                output_type=FilteredWordsResponse,
                system_prompt=self._read_prompt(filter_prompt_path),
                retries=3,
            )
            self.is_configured = True
        except Exception as error:
            logger.warning(
                "LLM provider initialization skipped (%s). Running in offline mode without AI enrichment.",
                error,
            )
            self.is_configured = False

    def _read_prompt(self, path: str) -> str:
        """Read a prompt template from disk."""
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    @property
    def model_name(self) -> str:
        """Return the primary configured model spec."""
        return self._model_name

    @property
    def structured_model_name(self) -> str:
        """Return the structured model spec."""
        return self._structured_model_name

    def translate_sentence(
        self,
        title: str,
        context: str,
        target_sentence: str,
    ) -> SentenceTranslation:
        """Generate translation and hints for a single sentence."""
        return asyncio.run(
            self.translate_sentence_async(title, context, target_sentence)
        )

    async def translate_sentence_with_usage_async(
        self,
        title: str,
        context: str,
        target_sentence: str,
    ) -> tuple[SentenceTranslation, Any]:
        """Generate translation and hints asynchronously, returning both output and usage."""
        if not self.is_configured or self._translation_agent is None:
            raise LlmNotConfiguredError("LLM provider credentials are not configured.")

        input_data = (
            f"TITLE: {title}\n"
            f"CONTEXT: {context}\n"
            f"TARGET_SENTENCE: {target_sentence}"
        )

        logger.info(
            "Starting translation request; input_chars=%d",
            len(input_data),
        )
        async with self._semaphore:
            result = await self._translation_agent.run(input_data)
        usage = result.usage()
        logger.info("Translation completed; usage=%s", usage)

        return result.output, usage

    async def translate_sentence_async(
        self,
        title: str,
        context: str,
        target_sentence: str,
    ) -> SentenceTranslation:
        """Generate translation and hints asynchronously."""
        output, usage = await self.translate_sentence_with_usage_async(
            title=title,
            context=context,
            target_sentence=target_sentence,
        )
        setattr(output, "usage", usage)
        return output

    def generate_practice_sentences(
        self,
        words: list[str],
    ) -> PracticeSentencesResponse:
        """Generate practice sentences for a vocabulary list."""
        return asyncio.run(self.generate_practice_sentences_async(words))

    async def generate_practice_sentences_with_usage_async(
        self,
        words: list[str],
    ) -> tuple[PracticeSentencesResponse, Any]:
        """Generate practice sentences asynchronously, returning both output and usage."""
        if not self.is_configured or self._practice_agent is None:
            raise LlmNotConfiguredError("LLM provider credentials are not configured.")

        input_data = f"WORDS: {json.dumps(words, ensure_ascii=False)}"

        logger.info(
            "Starting practice-sentence request; input_chars=%d",
            len(input_data),
        )
        async with self._semaphore:
            result = await self._practice_agent.run(input_data)
        usage = result.usage()
        logger.info(
            "Practice-sentence generation completed; usage=%s",
            usage,
        )

        return result.output, usage

    async def generate_practice_sentences_async(
        self,
        words: list[str],
    ) -> PracticeSentencesResponse:
        """Generate practice sentences asynchronously."""
        output, usage = await self.generate_practice_sentences_with_usage_async(words)
        setattr(output, "usage", usage)
        return output

    def extract_metadata(self, text: str) -> GeneratedMetadata:
        """Extract title and difficulty level from text."""
        if not self.is_configured or self._metadata_agent is None:
            raise LlmNotConfiguredError("LLM provider credentials are not configured.")

        input_data = f"TEXT:\n{text[:2000]}"

        logger.info(
            "Starting metadata request; input_chars=%d",
            len(input_data),
        )
        result = self._metadata_agent.run_sync(input_data)
        logger.info("Metadata extraction completed; usage=%s", result.usage())

        return result.output

    def filter_meaningful_words(
        self,
        raw_frequencies: list[dict],
        language: str,
    ) -> FilteredWordsResponse:
        """Filter raw word frequencies into meaningful dictionary lemmas."""
        if not self.is_configured or self._filter_agent is None:
            raise LlmNotConfiguredError("LLM provider credentials are not configured.")

        input_data = (
            f"LANGUAGE: {language}\n"
            "RAW_FREQUENCIES: "
            f"{json.dumps(raw_frequencies, ensure_ascii=False)}"
        )

        logger.info(
            "Starting word-filter request; input_chars=%d",
            len(input_data),
        )
        result = self._filter_agent.run_sync(input_data)
        logger.info("Word filtering completed; usage=%s", result.usage())

        return result.output
