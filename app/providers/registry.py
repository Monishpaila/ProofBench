from __future__ import annotations

import os
from typing import Any

from app.config import env_csv, get_model_pricing
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import ModelProvider, ProviderError
from app.providers.compatible_provider import OpenAICompatibleProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider

PROVIDER_META = {
    "openai": {"label": "OpenAI", "env_key": "OPENAI_API_KEY", "accent": "openai", "description": "GPT models using Chat Completions and native function calling."},
    "gemini": {"label": "Google Gemini", "env_key": "GOOGLE_API_KEY", "accent": "gemini", "description": "Gemini models using generateContent and function calling."},
    "anthropic": {"label": "Anthropic", "env_key": "ANTHROPIC_API_KEY", "accent": "anthropic", "description": "Claude models using the Messages API and tool use."},
    "openai_compatible": {"label": "OpenAI-compatible", "env_key": "OPENAI_COMPATIBLE_BASE_URL", "accent": "compatible", "description": "Local or hosted OpenAI-compatible endpoints, including supported local servers."},
}


def provider_configured(provider_id: str) -> bool:
    if provider_id == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    if provider_id == "gemini":
        return bool((os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip())
    if provider_id == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    if provider_id == "openai_compatible":
        return bool(os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip())
    return False


def list_models() -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    catalog = [
        ("openai", env_csv("PROOFBENCH_OPENAI_MODELS", "gpt-4o-mini,gpt-4.1-mini")),
        ("gemini", env_csv("PROOFBENCH_GEMINI_MODELS", "gemini-2.5-flash,gemini-2.5-pro")),
        ("anthropic", env_csv("PROOFBENCH_ANTHROPIC_MODELS", "claude-3-5-haiku-latest,claude-3-7-sonnet-latest")),
        ("openai_compatible", env_csv("PROOFBENCH_COMPATIBLE_MODELS", "llama3.1")),
    ]
    for provider_id, model_ids in catalog:
        for model_id in model_ids:
            pricing, price_source = get_model_pricing(model_id)
            models.append({
                "id": model_id,
                "provider": provider_id,
                "provider_label": PROVIDER_META[provider_id]["label"],
                "configured": provider_configured(provider_id),
                "tools_supported": True,
                "pricing": pricing,
                "price_source": price_source,
                "description": PROVIDER_META[provider_id]["description"],
            })
    return models


def get_model(model_id: str) -> dict[str, Any]:
    for model in list_models():
        if model["id"] == model_id:
            return model
    raise ProviderError(f"Model '{model_id}' is not in the configured model catalog. Add it to the appropriate PROOFBENCH_*_MODELS variable.")


def get_provider(provider_id: str) -> ModelProvider:
    providers: dict[str, type] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }
    provider_cls = providers.get(provider_id)
    if provider_cls is None:
        raise ProviderError(f"Unsupported provider '{provider_id}'.")
    return provider_cls()
