from __future__ import annotations

import os
from typing import Any

import httpx

from app.providers.base import ProviderError, ProviderResponse
from app.providers.common import (
    available_tools, has_usage, max_tool_rounds, parse_usage, record_tool_call,
    request_json, run_local_tool, timeout_seconds, tool_result_for_provider,
)


class GeminiProvider:
    provider_id = "gemini"
    base_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/"

    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()

    def generate(self, model_id: str, system: str, prompt: str, enable_tools: bool = True) -> ProviderResponse:
        if not self.api_key:
            raise ProviderError("GOOGLE_API_KEY (or GEMINI_API_KEY) is not configured. Add it to your environment and restart ProofBench.")
        tool_specs = available_tools() if enable_tools else []
        declarations = [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tool_specs]
        contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1200},
        }
        if declarations:
            payload["tools"] = [{"functionDeclarations": declarations}]
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        calls_log: list[dict[str, Any]] = []
        total_input = total_output = 0
        usage_reported = True
        with httpx.Client(timeout=timeout_seconds()) as client:
            for round_index in range(max_tool_rounds() + 1):
                url = f"{self.base_endpoint}{model_id}:generateContent"
                data = request_json(client, "POST", url, headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key}, payload=payload, provider_name="Gemini")
                usage_in, usage_out = parse_usage(data.get("usageMetadata"), "promptTokenCount", "candidatesTokenCount")
                total_input += usage_in
                total_output += usage_out
                usage_reported = usage_reported and has_usage(data.get("usageMetadata"), "promptTokenCount", "candidatesTokenCount")
                candidates = data.get("candidates") or []
                if not candidates:
                    raise ProviderError("Gemini returned no candidates")
                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                function_calls = [p.get("functionCall") for p in parts if isinstance(p, dict) and isinstance(p.get("functionCall"), dict)]
                if not function_calls:
                    text = "\n".join(str(p.get("text", "")) for p in parts if isinstance(p, dict) and "text" in p)
                    return ProviderResponse(text=text, input_tokens=total_input if usage_reported else 0, output_tokens=total_output if usage_reported else 0, usage_reported=usage_reported, tool_calls=calls_log)
                if round_index >= max_tool_rounds():
                    raise ProviderError("Gemini agent reached the maximum tool-call rounds without a final answer.")
                contents.append({"role": "model", "parts": parts})
                responses = []
                for call in function_calls:
                    name = str(call.get("name", ""))
                    arguments = call.get("args") if isinstance(call.get("args"), dict) else {}
                    result = run_local_tool(name, arguments) if enable_tools else {"ok": False, "error": "Tools are disabled for this run."}
                    record_tool_call(calls_log, name, arguments, result)
                    responses.append({"functionResponse": {"name": name, "response": result}})
                contents.append({"role": "user", "parts": responses})
                payload["contents"] = contents
        raise ProviderError("Gemini agent reached the maximum tool-call rounds without a final answer.")
