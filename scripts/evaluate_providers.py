"""Small opt-in, billable provider check using only synthetic language examples.

Run from the repository root: uv run python scripts/evaluate_providers.py
Uses the application's shared quota/budget ledger, never reads library texts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/backend"))

from core.settings import Settings
from core.database import engine, init_db
from services.llm_service import LlmService
from services.provider_governor import ProviderGovernor

EXAMPLES = [
    ("German", "Ich stehe früh auf, weil der Zug um sieben Uhr abfährt."),
    ("French", "Si j'avais su, je serais venu plus tôt."),
    ("Italian", "Non vedo l'ora di rivederti."),
    ("Spanish", "Se me olvidaron las llaves en casa."),
    ("English", "She had been waiting for an hour when the train finally arrived."),
]
MODELS = ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b", "deepseek:deepseek-flash"]


async def evaluate(models: list[str], output_path: Path) -> None:
    init_db()
    settings = Settings(groq_max_wait_seconds=65)
    governor = ProviderGovernor(engine, settings)
    rows = []
    for model in models:
        service = LlmService(str(settings.translation_prompt_file), str(settings.practice_prompt_file),
                             model, model, [], governor=governor)
        if not service.is_configured:
            print(f"{model}: missing key", flush=True)
            continue
        try:
            tasks = [("translation", language, sentence) for language, sentence in EXAMPLES]
            tasks += [("metadata", "French", EXAMPLES[1][1]), ("practice", "Spanish", ["llave", "casa", "olvidar"])]
            for task, language, source in tasks:
                started = time.monotonic()
                row: dict[str, Any] = {"model": model, "task": task, "language": language, "source": source}
                try:
                    if task == "translation":
                        result = await service.translate_sentence_async("Synthetic evaluation", "", str(source),
                                    owner_id="provider-evaluation", source_language=language)
                    elif task == "metadata":
                        result = await asyncio.to_thread(service.extract_metadata, str(source), "provider-evaluation")
                    else:
                        result = await service.generate_practice_sentences_async(list(source),
                                    owner_id="provider-evaluation", source_language=language)
                    row["output"] = result.model_dump(exclude={"usage", "provider", "model"})
                except Exception as error:
                    row["error"] = f"{type(error).__name__}: {error}"
                row["seconds"] = round(time.monotonic() - started, 2)
                rows.append(row)
                output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
                print(f"{model} {task}/{language}: {'ERROR' if 'error' in row else 'OK'} {row['seconds']}s", flush=True)
        finally:
            await service.aclose()
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", choices=MODELS)
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/typeandlearn-provider-evaluation.json"))
    args = parser.parse_args()
    asyncio.run(evaluate(args.model or MODELS, args.output))
