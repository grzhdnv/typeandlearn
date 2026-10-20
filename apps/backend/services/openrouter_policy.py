"""Free-only OpenRouter inference policy; no automatic router or paid variants."""

from decimal import Decimal, InvalidOperation

FREE_ROUTING = {
    "allow_fallbacks": False,
    "require_parameters": True,
    "max_price": {"prompt": 0, "completion": 0, "request": 0},
}


TOOL_OUTPUT_MODELS = frozenset({
    "nvidia/nemotron-3-ultra-550b-a55b:free",
})


def uses_native_output(model: str) -> bool:
    return model not in TOOL_OUTPUT_MODELS and not uses_prompted_output(model)


def uses_prompted_output(model: str) -> bool:
    return model == "minimax/minimax-m3.1-flash:free"


def reasoning_settings(model: str) -> dict:
    # MiniMax M3.1 Flash requires reasoning; use its lowest advertised effort.
    return {"effort": "low"} if model == "minimax/minimax-m3.1-flash:free" else {"enabled": False}


def validate_free_model(model: str, catalog: dict, *, native: bool = True, prompted: bool = False) -> dict:
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
    if prompted:
        required = {"response_format"}
    elif native:
        required = {"structured_outputs", "response_format"}
    else:
        required = {"tools", "tool_choice"}
    required.add("reasoning")
    reasoning = entry.get("reasoning") or {}
    requested_reasoning = reasoning_settings(model)
    if reasoning.get("mandatory") and requested_reasoning.get("enabled") is False:
        raise ValueError("Mandatory reasoning requires an explicit supported model policy")
    if "effort" in requested_reasoning and requested_reasoning["effort"] not in reasoning.get("supported_efforts", []):
        raise ValueError("The model no longer advertises the configured reasoning effort")
    if not required <= set(entry.get("supported_parameters", [])):
        raise ValueError("Model does not advertise the required structured-output parameters")
    return entry
