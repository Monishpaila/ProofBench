from __future__ import annotations

import os
from typing import Any

import httpx

from app.providers.base import ProviderError, ProviderResponse
from app.providers.common import (
    available_tools, has_usage, max_tool_rounds, parse_json_arguments, parse_usage,
    record_tool_call, request_json, run_local_tool, timeout_seconds,
)


class OpenAICompatibleProvider:
    """Adapter for local or hosted OpenAI-compatible chat-completions endpoints."""
    provider_id = "openai_compatible"

    def __init__(self) -> None:
        self.base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip().rstrip("/")
        self.api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()

    def generate(self, model_id: str, system: str, prompt: str, enable_tools: bool = True) -> ProviderResponse:
        if not self.base_url:
            raise ProviderError("OPENAI_COMPATIBLE_BASE_URL is not configured.")
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        tool_specs = available_tools() if enable_tools else []
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tool_specs]
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        calls_log: list[dict[str, Any]] = []
        total_input = total_output = 0
        usage_reported = True
        with httpx.Client(timeout=timeout_seconds()) as client:
            for round_index in range(max_tool_rounds() + 1):
                payload: dict[str, Any] = {"model": model_id, "messages": messages, "temperature": 0}
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                data = request_json(client, "POST", endpoint, headers=headers, payload=payload, provider_name="OpenAI-compatible endpoint")
                usage_in, usage_out = parse_usage(data.get("usage"), "prompt_tokens", "completion_tokens")
                total_input += usage_in
                total_output += usage_out
                usage_reported = usage_reported and has_usage(data.get("usage"), "prompt_tokens", "completion_tokens")
                choices = data.get("choices") or []
                if not choices:
                    raise ProviderError("OpenAI-compatible endpoint returned no completion choices")
                message = choices[0].get("message") or {}
                pending_calls = message.get("tool_calls") or []
                messages.append({"role": "assistant", "content": message.get("content"), **({"tool_calls": pending_calls} if pending_calls else {})})
                if not pending_calls:
                    return ProviderResponse(text=str(message.get("content") or ""), input_tokens=total_input if usage_reported else 0, output_tokens=total_output if usage_reported else 0, usage_reported=usage_reported, tool_calls=calls_log)
                if round_index >= max_tool_rounds():
                    raise ProviderError("OpenAI-compatible agent reached the maximum tool-call rounds without a final answer.")
                for call in pending_calls:
                    function = call.get("function") or {}
                    name = str(function.get("name", ""))
                    arguments = parse_json_arguments(function.get("arguments", "{}"))
                    result = run_local_tool(name, arguments) if enable_tools else {"ok": False, "error": "Tools are disabled for this run."}
                    record_tool_call(calls_log, name, arguments, result)
                    messages.append({"role": "tool", "tool_call_id": str(call.get("id", "")), "content": __import__("json").dumps(result, ensure_ascii=False)})
        raise ProviderError("OpenAI-compatible agent reached the maximum tool-call rounds without a final answer.")
