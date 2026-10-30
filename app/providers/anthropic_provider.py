from __future__ import annotations

import os
from typing import Any

import httpx

from app.providers.base import ProviderError, ProviderResponse
from app.providers.common import (
    available_tools, has_usage, max_tool_rounds, parse_usage, record_tool_call,
    request_json, run_local_tool, timeout_seconds, tool_result_for_provider,
)


class AnthropicProvider:
    provider_id = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    def generate(self, model_id: str, system: str, prompt: str, enable_tools: bool = True) -> ProviderResponse:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured. Add it to your environment and restart ProofBench.")
        tool_specs = available_tools() if enable_tools else []
        tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tool_specs]
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        calls_log: list[dict[str, Any]] = []
        total_input = total_output = 0
        usage_reported = True
        with httpx.Client(timeout=timeout_seconds()) as client:
            for round_index in range(max_tool_rounds() + 1):
                payload: dict[str, Any] = {"model": model_id, "max_tokens": 1200, "temperature": 0, "system": system, "messages": messages}
                if tools:
                    payload["tools"] = tools
                data = request_json(client, "POST", self.endpoint, headers={
                    "x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json",
                }, payload=payload, provider_name="Anthropic")
                usage_in, usage_out = parse_usage(data.get("usage"), "input_tokens", "output_tokens")
                total_input += usage_in
                total_output += usage_out
                usage_reported = usage_reported and has_usage(data.get("usage"), "input_tokens", "output_tokens")
                blocks = data.get("content") or []
                tool_uses = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
                if not tool_uses:
                    text = "\n".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict) and b.get("type") == "text")
                    return ProviderResponse(text=text, input_tokens=total_input if usage_reported else 0, output_tokens=total_output if usage_reported else 0, usage_reported=usage_reported, tool_calls=calls_log)
                if round_index >= max_tool_rounds():
                    raise ProviderError("Anthropic agent reached the maximum tool-call rounds without a final answer.")
                messages.append({"role": "assistant", "content": blocks})
                results = []
                for call in tool_uses:
                    name = str(call.get("name", ""))
                    arguments = call.get("input") if isinstance(call.get("input"), dict) else {}
                    result = run_local_tool(name, arguments) if enable_tools else {"ok": False, "error": "Tools are disabled for this run."}
                    record_tool_call(calls_log, name, arguments, result)
                    results.append({"type": "tool_result", "tool_use_id": str(call.get("id", "")), "content": tool_result_for_provider(result), "is_error": not bool(result.get("ok"))})
                messages.append({"role": "user", "content": results})
        raise ProviderError("Anthropic agent reached the maximum tool-call rounds without a final answer.")
