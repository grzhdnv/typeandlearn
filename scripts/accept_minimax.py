"""Opt-in synthetic MiniMax acceptance through real NLP/storage/enrichment services.

Learning data uses temporary SQLite; quota accounting uses the shared real ledger.
Only dictionary lookups are mocked. No paid fallback is configured.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any
from unittest.mock import Mock

from sqlmodel import SQLModel, Session, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.database import engine, init_db
from core.settings import Settings
from evaluate_providers import EvaluationTransport, preflight_openrouter
from models.providers import ProviderCallRecord
from repositories.cache_repository import CacheRepository
from repositories.job_repository import JobRepository
from repositories.text_repository import TextRepository
from services.dictionary_service import DictionaryService
from services.hint_validation import normalize_hints
from services.llm_service import LlmService
from services.preprocessing_service import PreprocessingService
from services.provider_governor import ProviderGovernor
from services.text_service import TextService

CASES = [
    ("German", "„Ich stehe früh auf“, sagt Anna. Am Bahnhof wartet sie, bis der Zug um sieben Uhr abfährt."),
    ("French", "Si j’avais su que le train était en retard, je serais venu plus tôt. Au marché, elle achète du pain, puis elle rentre chez elle."),
    ("Italian", "Non vedo l’ora di rivederti. Quando arrivi alla stazione, chiamami prima di comprare il biglietto."),
    ("Spanish", "¿Dónde dejaste la llave de la casa? Si olvido la llave, no puedo entrar en la casa."),
    ("English", "She had been waiting for an hour when the train finally arrived. Don’t forget your ticket, because you will need it again."),
]
MODEL = "openrouter:minimax/minimax-m3.1-flash:free"


async def main(output: Path, languages: list[str] | None = None) -> None:
    init_db()
    settings = Settings(openrouter_max_wait_seconds=65)
    await preflight_openrouter([MODEL], output, settings, minimum_requests=30)
    rows = []
    owner = "minimax-acceptance-2026-10-20"
    with tempfile.TemporaryDirectory(prefix="typeandlearn-minimax-", dir="/private/tmp") as folder:
        learning = create_engine(f"sqlite:///{folder}/learning.sqlite", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(learning)
        transport = EvaluationTransport()
        llm = LlmService(str(settings.translation_prompt_file), str(settings.practice_prompt_file), MODEL, MODEL, [],
                         governor=ProviderGovernor(engine, settings), transport=transport)
        dictionary = Mock(spec=DictionaryService)
        dictionary.translate_word.return_value = "Synthetic dictionary fixture"
        service = TextService(TextRepository(learning), llm, PreprocessingService(), dictionary,
                              job_repository=JobRepository(learning), cache_repository=CacheRepository(learning),
                              daily_token_limit=settings.daily_token_limit, prompt_version=settings.prompt_version)
        try:
            for language, text in CASES:
                if languages and language not in languages:
                    continue
                started = time.time()
                response_start = len(transport.responses)
                row: dict[str, Any] = {"language": language, "source": text}
                try:
                    # Existing service stdout contains source strings; do not echo it.
                    with redirect_stdout(io.StringIO()):
                        record = await asyncio.to_thread(service.upload, text, owner, language=language, filtering_method="llm")
                        if record.id is None:
                            raise ValueError("Uploaded synthetic text has no persistent ID")
                        await asyncio.to_thread(service.process_pending_text, record.id, owner)
                    data = service.get_one(str(record.id), owner)
                    row["saved"] = data.model_dump()
                    if data.status != "processed" or data.enrichment_stage != "completed":
                        raise ValueError(f"Enrichment ended with status={data.status}, stage={data.enrichment_stage}")
                    sentences = [s for p in data.original_paragraphs for s in p.sentences]
                    if len(sentences) < 2 or len(data.practice_sentences) != 5:
                        raise ValueError("Expected at least two translated sentences and five saved exercises")
                    for sentence in sentences:
                        normalize_hints(sentence.text, sentence.translation_hints)
                    for sentence in data.practice_sentences:
                        normalize_hints(sentence.sentence, sentence.translation_hints)
                    # Read again through a new repository/service instance to prove persistence.
                    restored = TextService(TextRepository(learning), llm, PreprocessingService(), dictionary).get_one(str(record.id), owner)
                    if restored.model_dump() != data.model_dump():
                        raise ValueError("Saved text changed after repository reload")
                    row["accepted"] = True
                except Exception as error:
                    row["accepted"] = False
                    row["error"] = f"{type(error).__name__}: {error}"
                with Session(engine) as session:
                    calls = session.exec(select(ProviderCallRecord).where(ProviderCallRecord.owner_id == owner, ProviderCallRecord.created_at >= started)).all()
                    row["calls"] = [{"task": c.task, "status": c.status, "status_code": c.status_code,
                                     "tokens": c.tokens, "cost_usd": c.cost_microusd / 1_000_000,
                                     "returned_model": c.response_model} for c in calls]
                row["responses"] = transport.responses[response_start:]
                row["seconds"] = round(time.time() - started, 2)
                rows.append(row)
                output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
                print(f"{language}: {'ACCEPTED' if row['accepted'] else 'FAILED'}; {len(row['calls'])} attempts; {row['seconds']}s", flush=True)
                if any(c["cost_usd"] > 0 or c["status_code"] in (401, 402, 403) for c in row["calls"]):
                    raise RuntimeError("Stopped on paid cost or account/budget error")
        finally:
            await llm.aclose()
            learning.dispose()
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", action="append", choices=[language for language, _ in CASES])
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/typeandlearn-minimax-acceptance.json"))
    args = parser.parse_args()
    asyncio.run(main(args.output, args.language))
