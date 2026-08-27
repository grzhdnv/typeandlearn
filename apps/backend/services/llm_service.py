"""Service for generating structured text data via an LLM provider."""

from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIModel
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
        return OpenAIModel(model_name, provider=provider, profile=profile)

    provider = GroqProvider(http_client=client)
    model_name = model_spec.removeprefix("groq:")
    return GroqModel(model_name, provider=provider)


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
        """Configure prompt sources and initialize Pydantic AI agents."""
        self._model_name = model_name
        self._translation_prompt = self._read_prompt(translation_prompt_path)
        self._practice_prompt = self._read_prompt(practice_prompt_path)
        client = httpx.AsyncClient(
            transport=_HeaderCaptureTransport(httpx.AsyncHTTPTransport())
        )

        primary_model = _create_model(model_name, client)
        structured_model = _create_model(structured_model_name, client)

        if fallback_models:
            fallbacks = [
                _create_model(fallback_model, client)
                for fallback_model in fallback_models
            ]
            self._active_model = FallbackModel(primary_model, *fallbacks)
            self._active_structured_model = FallbackModel(
                structured_model,
                *fallbacks,
            )
        else:
            self._active_model = primary_model
            self._active_structured_model = structured_model

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

    def _read_prompt(self, path: str) -> str:
        """Read a prompt template from disk."""
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

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

    async def translate_sentence_async(
        self,
        title: str,
        context: str,
        target_sentence: str,
    ) -> SentenceTranslation:
        """Generate translation and hints asynchronously."""
        input_data = (
            f"TITLE: {title}\n"
            f"CONTEXT: {context}\n"
            f"TARGET_SENTENCE: {target_sentence}"
        )

        logger.info(
            "Starting translation request; input_chars=%d",
            len(input_data),
        )
        result = await self._translation_agent.run(input_data)
        logger.info("Translation completed; usage=%s", result.usage())

        return result.output

    def generate_practice_sentences(
        self,
        words: list[str],
    ) -> PracticeSentencesResponse:
        """Generate practice sentences for a vocabulary list."""
        return asyncio.run(self.generate_practice_sentences_async(words))

    async def generate_practice_sentences_async(
        self,
        words: list[str],
    ) -> PracticeSentencesResponse:
        """Generate practice sentences asynchronously."""
        input_data = f"WORDS: {json.dumps(words, ensure_ascii=False)}"

        logger.info(
            "Starting practice-sentence request; input_chars=%d",
            len(input_data),
        )
        result = await self._practice_agent.run(input_data)
        logger.info(
            "Practice-sentence generation completed; usage=%s",
            result.usage(),
        )

        return result.output

    def extract_metadata(self, text: str) -> GeneratedMetadata:
        """Extract title and difficulty level from text."""
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
