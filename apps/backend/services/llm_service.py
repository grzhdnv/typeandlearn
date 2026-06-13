"""Service for generating structured text data via an LLM provider using Pydantic AI."""

import json
import logging
import os
import httpx
from typing import List

from pydantic_ai import Agent
from schemas.texts import PracticeSentencesResponse, SentenceTranslation, GeneratedMetadata, FilteredWordsResponse

# Create logs directory if it doesn't exist
os.makedirs("apps/backend/logs", exist_ok=True)

logger = logging.getLogger("typeandlearn.llm")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler("apps/backend/logs/llm.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)


class LlmService:
    """Generate translations and practice sentences using Pydantic AI."""

    def __init__(
        self,
        translation_prompt_path: str,
        practice_prompt_path: str,
        model_name: str,
        fallback_models: List[str] | None = None
    ) -> None:
        """Configure prompt sources and initialize Pydantic AI agents."""
        self._model_name = model_name
        self._translation_prompt = self._read_prompt(translation_prompt_path)
        self._practice_prompt = self._read_prompt(practice_prompt_path)
        
        class HeaderCaptureTransport(httpx.AsyncBaseTransport):
            def __init__(self, transport: httpx.AsyncBaseTransport):
                self._transport = transport

            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                response = await self._transport.handle_async_request(request)
                remaining_tokens = response.headers.get("x-ratelimit-remaining-tokens")
                if remaining_tokens:
                    logger.info(f"Groq Rate Limit - Remaining Tokens: {remaining_tokens}")
                return response
                
        client = httpx.AsyncClient(transport=HeaderCaptureTransport(httpx.AsyncHTTPTransport()))
        
        from pydantic_ai.models.fallback import FallbackModel
        def create_model(model_str: str):
            if model_str.startswith("deepseek:"):
                from pydantic_ai.models.openai import OpenAIModel
                from pydantic_ai.providers.deepseek import DeepSeekProvider
                ds_provider = DeepSeekProvider(http_client=client)
                return OpenAIModel(model_str.replace("deepseek:", ""), provider=ds_provider)
            else:
                from pydantic_ai.models.groq import GroqModel
                from pydantic_ai.providers.groq import GroqProvider
                groq_provider = GroqProvider(http_client=client)
                primary_model_str = model_str.replace("groq:", "") if model_str.startswith("groq:") else model_str
                return GroqModel(primary_model_str, provider=groq_provider)

        primary_model = create_model(model_name)
        
        if fallback_models:
            fallbacks = [create_model(fb) for fb in fallback_models]
            self._active_model = FallbackModel(primary_model, *fallbacks)
        else:
            self._active_model = primary_model
            
        self._translation_agent = Agent(
            self._active_model,
            output_type=SentenceTranslation,
            system_prompt=self._translation_prompt,
            retries=3
        )
        
        self._practice_agent = Agent(
            self._active_model,
            output_type=PracticeSentencesResponse,
            system_prompt=self._practice_prompt,
            retries=3
        )
        
        metadata_prompt_path = "apps/backend/prompts/metadata_prompt.txt"
        self._metadata_agent = Agent(
            self._active_model,
            output_type=GeneratedMetadata,
            system_prompt=self._read_prompt(metadata_prompt_path),
            retries=3
        )
        
        filter_prompt_path = "apps/backend/prompts/filter_words_prompt.txt"
        self._filter_agent = Agent(
            self._active_model,
            output_type=FilteredWordsResponse,
            system_prompt=self._read_prompt(filter_prompt_path),
            retries=3
        )

    def _read_prompt(self, path: str) -> str:
        """Read a prompt template from disk."""
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def translate_sentence(self, title: str, context: str, target_sentence: str) -> SentenceTranslation:
        """Generate translation and hints for a single sentence."""
        import asyncio
        return asyncio.run(self.translate_sentence_async(title, context, target_sentence))

    async def translate_sentence_async(self, title: str, context: str, target_sentence: str) -> SentenceTranslation:
        """Generate translation and hints for a single sentence asynchronously."""
        input_data = (
            f"TITLE: {title}\n"
            f"CONTEXT: {context}\n"
            f"TARGET_SENTENCE: {target_sentence}"
        )
        
        logger.info(f"--- LLM REQUEST (Translation) ---\nInput Data:\n{input_data}")
        result = await self._translation_agent.run(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n---------------------------------")
        
        return result.output

    def generate_practice_sentences(self, words: List[str]) -> PracticeSentencesResponse:
        """Generate distinct practice sentences based on a list of vocabulary words."""
        import asyncio
        return asyncio.run(self.generate_practice_sentences_async(words))

    async def generate_practice_sentences_async(self, words: List[str]) -> PracticeSentencesResponse:
        """Generate distinct practice sentences based on a list of vocabulary words asynchronously."""
        input_data = f"WORDS: {json.dumps(words, ensure_ascii=False)}"
        
        logger.info(f"--- LLM REQUEST (Practice) ---\nInput Data:\n{input_data}")
        result = await self._practice_agent.run(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n------------------------------")
        
        return result.output

    def extract_metadata(self, text: str) -> GeneratedMetadata:
        """Extract title and difficulty level from text."""
        input_data = f"TEXT:\n{text[:2000]}" # only need first 2k chars for title/difficulty
        
        logger.info(f"--- LLM REQUEST (Metadata) ---\nInput Data:\n{input_data}")
        result = self._metadata_agent.run_sync(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n------------------------------")
        
        return result.output

    def filter_meaningful_words(self, raw_frequencies: List[dict], language: str) -> FilteredWordsResponse:
        """Filter raw word frequencies into meaningful dictionary lemmas using the LLM."""
        input_data = (
            f"LANGUAGE: {language}\n"
            f"RAW_FREQUENCIES: {json.dumps(raw_frequencies, ensure_ascii=False)}"
        )
        
        logger.info(f"--- LLM REQUEST (Filter Words) ---\nInput Data:\n{input_data}")
        result = self._filter_agent.run_sync(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n------------------------------")
        
        return result.output
