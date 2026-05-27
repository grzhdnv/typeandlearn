"""Service for generating structured text data via an LLM provider using Pydantic AI."""

import json
import logging
import os
from typing import List

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

from pydantic_ai import Agent
from schemas.texts import PracticeSentencesResponse, SentenceTranslation


class LlmService:
    """Generate translations and practice sentences using Pydantic AI."""

    def __init__(
        self,
        translation_prompt_path: str,
        practice_prompt_path: str,
        model_name: str
    ) -> None:
        """Configure prompt sources and initialize Pydantic AI agents."""
        self._model_name = model_name
        self._translation_prompt = self._read_prompt(translation_prompt_path)
        self._practice_prompt = self._read_prompt(practice_prompt_path)
        
        self._translation_agent = Agent(
            self._model_name,
            output_type=SentenceTranslation,
            system_prompt=self._translation_prompt
        )
        
        self._practice_agent = Agent(
            self._model_name,
            output_type=PracticeSentencesResponse,
            system_prompt=self._practice_prompt
        )

    def _read_prompt(self, path: str) -> str:
        """Read a prompt template from disk."""
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def translate_sentence(self, title: str, context: str, target_sentence: str) -> SentenceTranslation:
        """Generate translation and hints for a single sentence."""
        input_data = (
            f"TITLE: {title}\n"
            f"CONTEXT: {context}\n"
            f"TARGET_SENTENCE: {target_sentence}"
        )
        
        logger.info(f"--- LLM REQUEST (Translation) ---\nInput Data:\n{input_data}")
        result = self._translation_agent.run_sync(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n---------------------------------")
        
        return result.output

    def generate_practice_sentences(self, words: List[str]) -> PracticeSentencesResponse:
        """Generate distinct practice sentences based on a list of vocabulary words."""
        input_data = f"WORDS: {json.dumps(words, ensure_ascii=False)}"
        
        logger.info(f"--- LLM REQUEST (Practice) ---\nInput Data:\n{input_data}")
        result = self._practice_agent.run_sync(input_data)
        logger.info(f"--- LLM RESPONSE ---\nTokens: {result.usage()}\nOutput:\n{result.output.model_dump_json(indent=2)}\n------------------------------")
        
        return result.output
