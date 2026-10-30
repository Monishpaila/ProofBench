"""Environment-based configuration for ProofBench.

Secrets are intentionally read only from environment variables and are never
returned by API endpoints or persisted to the application database.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_csv(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def get_database_path() -> Path:
    raw = os.getenv("PROOFBENCH_DB_PATH", str(APP_ROOT / "data" / "proofbench.db"))
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_timeout_seconds() -> float:
    try:
        return max(5.0, min(float(os.getenv("PROOFBENCH_REQUEST_TIMEOUT", "60")), 180.0))
    except ValueError:
        return 60.0


def get_max_tool_rounds() -> int:
    try:
        return max(1, min(int(os.getenv("PROOFBENCH_MAX_TOOL_ROUNDS", "4")), 8))
    except ValueError:
        return 4


def get_pricing_overrides() -> dict[str, dict[str, float]]:
    """Read per-million-token USD pricing overrides from JSON environment value."""
    raw = os.getenv("PROOFBENCH_MODEL_PRICING_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    clean: dict[str, dict[str, float]] = {}
    for model, rates in parsed.items():
        if not isinstance(model, str) or not isinstance(rates, dict):
            continue
        try:
            input_rate = float(rates.get("input_per_1m", 0))
            output_rate = float(rates.get("output_per_1m", 0))
        except (TypeError, ValueError):
            continue
        if input_rate >= 0 and output_rate >= 0:
            clean[model] = {"input_per_1m": input_rate, "output_per_1m": output_rate}
    return clean


# Indicative rates are for planning, not invoices. Providers update prices and
# model aliases; teams should override these rates with the current rate card.
# `estimated` is surfaced in every report that uses this bundled rate card.
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-4.1-mini": {"input_per_1m": 0.40, "output_per_1m": 1.60},
    "gemini-2.5-flash": {"input_per_1m": 0.30, "output_per_1m": 2.50},
    "gemini-2.5-pro": {"input_per_1m": 1.25, "output_per_1m": 10.00},
    "claude-3-5-haiku-latest": {"input_per_1m": 0.80, "output_per_1m": 4.00},
    "claude-3-7-sonnet-latest": {"input_per_1m": 3.00, "output_per_1m": 15.00},
}


def get_model_pricing(model_id: str) -> tuple[dict[str, float] | None, str]:
    overrides = get_pricing_overrides()
    if model_id in overrides:
        return overrides[model_id], "environment_override"
    if model_id in DEFAULT_PRICING:
        return DEFAULT_PRICING[model_id], "bundled_estimate"
    # Provider model names sometimes have dated or versioned suffixes.
    candidates = [name for name in DEFAULT_PRICING if model_id.startswith(name)]
    if candidates:
        best = max(candidates, key=len)
        return DEFAULT_PRICING[best], "bundled_estimate"
    return None, "unpriced"
