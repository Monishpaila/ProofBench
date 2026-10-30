from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class BenchmarkCase(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=240)
    category: str = Field(default="general", max_length=80)
    prompt: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=12000)
    reference_answer: str = Field(default="", max_length=6000)
    must_include: list[str] = Field(default_factory=list, max_length=30)
    must_not_include: list[str] = Field(default_factory=list, max_length=30)
    grounding_facts: list[str] = Field(default_factory=list, max_length=30)
    expected_tools: list[str] = Field(default_factory=list, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("expected_tools")
    @classmethod
    def known_tools_only(cls, value: list[str]) -> list[str]:
        allowed = {"lookup_order", "get_policy", "calculate_refund"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unsupported expected_tools: {', '.join(sorted(unknown))}")
        return value


class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="custom", max_length=80)
    cases: list[BenchmarkCase] = Field(min_length=1, max_length=250)


class DatasetUpdate(DatasetCreate):
    pass


class RunCreate(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=100)
    model_ids: list[str] = Field(min_length=1, max_length=8)
    workflow_ids: list[str] = Field(default_factory=lambda: ["tool_agent"], min_length=1, max_length=2)
    name: str | None = Field(default=None, max_length=120)
    # Backwards-compatible alias for clients using the first ProofBench API draft.
    enable_tools: bool | None = None

    @field_validator("model_ids")
    @classmethod
    def deduplicate_models(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(v.strip() for v in value if v.strip()))
        if not cleaned:
            raise ValueError("Select at least one model.")
        if len(cleaned) > 8:
            raise ValueError("A benchmark can compare up to 8 models at once.")
        return cleaned

    @field_validator("workflow_ids")
    @classmethod
    def validate_workflows(cls, value: list[str]) -> list[str]:
        allowed = {"direct", "tool_agent"}
        cleaned = list(dict.fromkeys(v.strip() for v in value if v.strip()))
        if not cleaned:
            raise ValueError("Select at least one workflow.")
        unknown = set(cleaned) - allowed
        if unknown:
            raise ValueError(f"Unsupported workflow IDs: {', '.join(sorted(unknown))}")
        return cleaned

    @model_validator(mode="after")
    def translate_legacy_tool_flag(self):
        if self.enable_tools is False and self.workflow_ids == ["tool_agent"]:
            self.workflow_ids = ["direct"]
        return self
