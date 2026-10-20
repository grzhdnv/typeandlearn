"""Free-only OpenRouter inference policy; no automatic router or paid variants."""

from decimal import Decimal, InvalidOperation

FREE_ROUTING = {
    "allow_fallbacks": False,
    "require_parameters": True,
    "max_price": {"prompt": 0, "completion": 0, "request": 0},
}


def validate_free_model(model: str, catalog: dict, *, native: bool = True) -> dict:
    if not model.endswith(":free") or "/" not in model:
        raise ValueError("An explicit :free model ID is required")
    entry = next((item for item in catalog.get("data", []) if item.get("id") == model), None)
    if entry is None:
        raise ValueError("Model is absent from the current catalog")
    prices = entry.get("pricing", {})
    try:
        if not {"prompt", "completion"} <= prices.keys() or any(Decimal(str(value)) != 0 for value in prices.values()):
            raise ValueError("Model pricing must be explicitly zero")
    except InvalidOperation as error:
        raise ValueError("Invalid model pricing") from error
    required = {"structured_outputs", "response_format"} if native else {"tools", "tool_choice"}
    required.add("reasoning")
    if (entry.get("reasoning") or {}).get("mandatory"):
        raise ValueError("This adapter requires optional reasoning so the output budget remains available")
    if not required <= set(entry.get("supported_parameters", [])):
        raise ValueError("Model does not advertise the required structured-output parameters")
    return entry
