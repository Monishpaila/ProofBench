from __future__ import annotations

import os
from typing import Any

import httpx

from app.providers.base import ProviderError, ProviderResponse
from app.providers.common import (
    available_tools, has_usage, max_tool_rounds, parse_json_arguments, parse_usage,
    record_tool_call, request_json, run_local_tool, timeout_seconds,
)


class OpenAIProvider:
    provider_id = "openai"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()

    def generate(self, model_id: str, system: str, prompt: str, enable_tools: bool = True) -> ProviderResponse:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not configured. Add it to your environment and restart ProofBench.")
        tool_specs = available_tools() if enable_tools else []
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tool_specs]
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        calls_log: list[dict[str, Any]] = []
        total_input = 0
        total_output = 0
        usage_reported = True
        with httpx.Client(timeout=timeout_seconds()) as client:
            for round_index in range(max_tool_rounds() + 1):
                payload: dict[str, Any] = {"model": model_id, "messages": messages, "temperature": 0}
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                data = request_json(client, "POST", self.endpoint, headers={
                    "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                }, payload=payload, provider_name="OpenAI")
                usage_in, usage_out = parse_usage(data.get("usage"), "prompt_tokens", "completion_tokens")
                total_input += usage_in
                total_output += usage_out
                usage_reported = usage_reported and has_usage(data.get("usage"), "prompt_tokens", "completion_tokens")
                choices = data.get("choices") or []
                if not choices or not isinstance(choices[0], dict):
                    raise ProviderError("OpenAI returned no completion choices")
                message = choices[0].get("message") or {}
                pending_calls = message.get("tool_calls") or []
                messages.append({"role": "assistant", "content": message.get("content"), **({"tool_calls": pending_calls} if pending_calls else {})})
                if not pending_calls:
                    text = message.get("content")
                    if isinstance(text, list):
                        text = "\n".join(str(part.get("text", "")) for part in text if isinstance(part, dict))
                    return ProviderResponse(
                        text=str(text or ""), input_tokens=total_input if usage_reported else 0, output_tokens=total_output if usage_reported else 0, usage_reported=usage_reported,
                        tool_calls=calls_log,
                    )
                if round_index >= max_tool_rounds():
                    raise ProviderError("OpenAI agent reached the maximum tool-call rounds without a final answer.")
                for call in pending_calls:
                    function = call.get("function") or {}
                    name = str(function.get("name", ""))
                    arguments = parse_json_arguments(function.get("arguments", "{}"))
                    if not enable_tools:
                        result = {"ok": False, "error": "Tools are disabled for this run."}
                    else:
                        result = run_local_tool(name, arguments)
                    record_tool_call(calls_log, name, arguments, result)
                    messages.append({"role": "tool", "tool_call_id": str(call.get("id", "")), "content": __import__("json").dumps(result, ensure_ascii=False)})
        raise ProviderError("OpenAI agent reached the maximum tool-call rounds without a final answer.")
