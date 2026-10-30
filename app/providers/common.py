from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.config import get_max_tool_rounds, get_timeout_seconds
from app.providers.base import ProviderError, ProviderResponse
from app.tools import TOOL_DESCRIPTIONS, execute_tool


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    provider_name: str,
) -> dict[str, Any]:
    """Request JSON with bounded retries for transient upstream failures."""
    last_error = "request failed"
    for attempt in range(3):
        try:
            response = client.request(method, url, headers=headers, json=payload)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                last_error = f"{provider_name} returned HTTP {response.status_code}"
                if attempt < 2:
                    time.sleep(0.4 * (attempt + 1))
                    continue
            if not response.is_success:
                try:
                    body = response.json()
                    detail = body.get("error", body.get("message", ""))
                    if isinstance(detail, dict):
                        detail = detail.get("message", "")
                    detail = str(detail)[:240]
                except (ValueError, AttributeError):
                    detail = ""
                suffix = f": {detail}" if detail else ""
                raise ProviderError(f"{provider_name} returned HTTP {response.status_code}{suffix}")
            try:
                data = response.json()
            except ValueError as exc:
                raise ProviderError(f"{provider_name} returned an invalid JSON response") from exc
            if not isinstance(data, dict):
                raise ProviderError(f"{provider_name} returned an unexpected response shape")
            return data
        except ProviderError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            last_error = f"{provider_name} request failed ({type(exc).__name__})"
            if attempt < 2:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise ProviderError(f"{last_error}; check network access and provider configuration") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"{provider_name} request failed ({type(exc).__name__})") from exc
    raise ProviderError(last_error)


def available_tools() -> list[dict[str, Any]]:
    return [
        {"name": name, **definition}
        for name, definition in TOOL_DESCRIPTIONS.items()
    ]


def run_local_tool(name: str, arguments: dict[str, Any] | str | None) -> dict[str, Any]:
    result = execute_tool(name, arguments)
    return result


def record_tool_call(
    log: list[dict[str, Any]], name: str, arguments: dict[str, Any] | str | None, result: dict[str, Any]
) -> None:
    log.append({
        "name": name,
        "arguments": arguments if isinstance(arguments, (dict, str)) else {},
        "ok": bool(result.get("ok")),
        "result": result,
    })


def max_tool_rounds() -> int:
    return get_max_tool_rounds()


def timeout_seconds() -> float:
    return get_timeout_seconds()


def parse_json_arguments(value: Any) -> dict[str, Any] | str:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return value
    return {}


def estimate_tokens(text: str) -> int:
    """Fallback tokenizer estimate only when a provider omits usage metadata."""
    return max(1, len(text) // 4) if text else 0


def parse_usage(value: Any, input_key: str, output_key: str) -> tuple[int, int]:
    if not isinstance(value, dict):
        return 0, 0
    try:
        return max(0, int(value.get(input_key, 0) or 0)), max(0, int(value.get(output_key, 0) or 0))
    except (TypeError, ValueError):
        return 0, 0


def tool_result_for_provider(result: dict[str, Any]) -> str:
    # Kept as JSON text across provider interfaces so tool outputs are auditable.
    return json.dumps(result, ensure_ascii=False, sort_keys=True)


def has_usage(value: Any, input_key: str, output_key: str) -> bool:
    """True only when upstream explicitly supplied both token counts."""
    return isinstance(value, dict) and input_key in value and output_key in value
