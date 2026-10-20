"""Small opt-in, billable provider check using only synthetic language examples.

Run from the repository root: uv run python scripts/evaluate_providers.py
Uses the application's shared quota/budget ledger, never reads library texts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

import httpx
from sqlmodel import Session, select, col
from pathlib import Path
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/backend"))

from core.settings import Settings
from core.database import engine, init_db
from services.llm_service import LlmService
from services.provider_governor import ProviderGovernor
from models.providers import ProviderCallRecord
from services.openrouter_policy import validate_free_model
from pydantic_ai.exceptions import ModelHTTPError

EXAMPLES = [
    ("German", "Ich stehe früh auf, weil der Zug um sieben Uhr abfährt."),
    ("French", "Si j'avais su, je serais venu plus tôt."),
    ("Italian", "Non vedo l'ora di rivederti."),
    ("Spanish", "Se me olvidaron las llaves en casa."),
    ("English", "She had been waiting for an hour when the train finally arrived."),
]
MODELS = ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b", "deepseek:deepseek-flash"]

OPENROUTER_MODELS = [
    "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter:dots-studio/dots-3-note-preview:free",
    "openrouter:nvidia/nemotron-3-super-120b-a12b:free",
]


async def preflight_openrouter(models: list[str], output_path: Path, settings: Settings) -> None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Set OPENROUTER_API_KEY in the ignored .env file")
    async with httpx.AsyncClient(timeout=30) as client:
        catalog_response = await client.get("https://openrouter.ai/api/v1/models")
        catalog_response.raise_for_status()
        entries = [validate_free_model(spec.split(":", 1)[1], catalog_response.json(), native="nemotron-3-ultra-" not in spec) for spec in models]
        key_response = await client.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"})
        key_response.raise_for_status()
        data = key_response.json()["data"]
        if data.get("is_management_key") or data.get("is_provisioning_key"):
            raise RuntimeError("Use an inference key from https://openrouter.ai/settings/keys, not a management key")
        quota = data.get("free_model_daily_requests")
        evidence = {"checked_at_unix": time.time(), "models": entries, "free_model_daily_requests": quota,
                    "is_free_tier": data.get("is_free_tier"),
                    "configuration": {"reasoning_enabled": False, "max_output_tokens": settings.llm_max_output_tokens,
                                      "openrouter_rpd": settings.openrouter_rpd, "openrouter_rpm": settings.openrouter_rpm,
                                      "daily_token_limit": settings.daily_token_limit}}
        output_path.with_suffix(".preflight.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
        print(f"OpenRouter free quota: {quota or 'not reported'}", flush=True)
        if quota is not None and quota.get("remaining", 0) < len(models) * 7:
            raise RuntimeError("Insufficient remaining free allowance for seven cases per model")


def safe_provider_error(body: Any) -> dict | None:
    if not isinstance(body, dict):
        return None
    metadata = body.get("metadata") or {}
    return {"code": body.get("code"), "message": body.get("message"),
            "provider": metadata.get("provider_name") if isinstance(metadata, dict) else None}


def error_summary(error: Exception) -> str:
    if isinstance(error, ModelHTTPError):
        return f"ModelHTTPError: status_code: {error.status_code}, model_name: {error.model_name}, error: {safe_provider_error(error.body)}"
    return f"{type(error).__name__}: {error}"


class EvaluationTransport(httpx.AsyncHTTPTransport):
    """Record synthetic final outputs and usage, excluding headers and reasoning text."""

    def __init__(self):
        super().__init__(retries=0)
        self.responses: list[dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await super().handle_async_request(request)
        if request.method == "POST":
            await response.aread()
            try:
                body = response.json()
            except ValueError:
                body = {}
            choices = []
            for choice in body.get("choices", []):
                message = choice.get("message") or {}
                choices.append({"finish_reason": choice.get("finish_reason"),
                                "content": message.get("content"), "tool_calls": message.get("tool_calls")})
            self.responses.append({"status_code": response.status_code, "model": body.get("model"),
                                   "provider": body.get("provider"), "usage": body.get("usage"),
                                   "choices": choices, "error": safe_provider_error(body.get("error"))})
        return response


async def evaluate(models: list[str], output_path: Path, resume: bool = False) -> None:
    init_db()
    settings = Settings(groq_max_wait_seconds=65, openrouter_max_wait_seconds=65)
    if all(model.startswith("openrouter:") for model in models):
        await preflight_openrouter(models, output_path, settings)
    governor = ProviderGovernor(engine, settings)
    rows = json.loads(output_path.read_text()) if resume and output_path.exists() else []
    for model in models:
        transport = EvaluationTransport()
        service = LlmService(str(settings.translation_prompt_file), str(settings.practice_prompt_file),
                             model, model, [], governor=governor, transport=transport)
        if not service.is_configured:
            print(f"{model}: missing key", flush=True)
            continue
        try:
            tasks = [("translation", language, sentence) for language, sentence in EXAMPLES]
            tasks += [("metadata", "French", EXAMPLES[1][1]), ("practice", "Spanish", ["llave", "casa", "olvidar"])]
            for task, language, source in tasks:
                previous = next((r for r in rows if (r["model"], r["task"], r["language"]) == (model, task, language)), None)
                if previous and "output" in previous:
                    continue
                response_start = len(transport.responses)
                fatal_error = False
                started = time.monotonic()
                started_wall = time.time()
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
                    row["error"] = error_summary(error)
                    fatal_error = isinstance(error, ModelHTTPError) and error.status_code in (401, 402, 403)
                row["responses"] = transport.responses[response_start:]
                with Session(engine) as session:
                    calls = session.exec(select(ProviderCallRecord).where(
                        ProviderCallRecord.owner_id == "provider-evaluation",
                        ProviderCallRecord.created_at >= started_wall,
                    ).order_by(col(ProviderCallRecord.created_at))).all()
                    row["calls"] = [{"provider": call.provider, "requested_model": call.model,
                                     "returned_model": call.response_model, "status": call.status,
                                     "status_code": call.status_code, "tokens": call.tokens,
                                     "cost_usd": call.cost_microusd / 1_000_000,
                                     "dispatch_delay_seconds": round(call.created_at - started_wall, 2)} for call in calls]
                row["seconds"] = round(time.monotonic() - started, 2)
                if previous:
                    row["previous_attempts"] = [*previous.get("previous_attempts", []), {k: v for k, v in previous.items() if k != "previous_attempts"}]
                    rows[rows.index(previous)] = row
                else:
                    rows.append(row)
                output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
                print(f"{model} {task}/{language}: {'ERROR' if 'error' in row else 'OK'} {row['seconds']}s", flush=True)
                if any(call["cost_usd"] > 0 for call in row["calls"]):
                    raise RuntimeError("Unexpected nonzero cost in free-only evaluation; stopped")
                if fatal_error or any(call["status_code"] in (401, 402, 403) for call in row["calls"]):
                    raise RuntimeError("Evaluation stopped on authentication, budget, or access error; see saved results")
        finally:
            await service.aclose()
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", choices=MODELS + OPENROUTER_MODELS)
    parser.add_argument("--resume", action="store_true", help="Keep successful cases in the output file and retry unfinished cases once; preserve prior failures")
    parser.add_argument("--openrouter-free", action="store_true", help="Compare only the explicit free OpenRouter shortlist; no paid fallback")
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/typeandlearn-provider-evaluation.json"))
    args = parser.parse_args()
    if args.openrouter_free and args.model:
        parser.error("Use --openrouter-free or --model, not both")
    asyncio.run(evaluate(OPENROUTER_MODELS if args.openrouter_free else args.model or MODELS, args.output, args.resume))
