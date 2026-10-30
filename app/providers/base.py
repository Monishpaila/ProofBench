from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProviderResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    usage_reported: bool = False
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class ModelProvider(Protocol):
    provider_id: str

    def generate(self, model_id: str, system: str, prompt: str, enable_tools: bool = True) -> ProviderResponse:
        ...


class ProviderError(RuntimeError):
    """An upstream provider error safe to surface in a benchmark result."""
