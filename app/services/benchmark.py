from __future__ import annotations

import json
import time
from typing import Any

from app.config import get_model_pricing
from app.database import connect, decode_json, utc_now
from app.providers.base import ProviderError
from app.providers.registry import get_model, get_provider
from app.services.evaluation import EVALUATOR_VERSION, evaluate_case

SYSTEM_PROMPT = """You are an assistant being evaluated on a business workflow. Follow the user's instruction precisely. Use provided context as authoritative. Do not invent facts, policies, dates, order status, or compensation. When an order or approved policy must be checked, use the available tools. If a tool says information is not found, be transparent. Keep the response concise and helpful."""
DIRECT_SYSTEM_PROMPT = SYSTEM_PROMPT + "\nThis is the direct-answer workflow: no external tools are available. Do not claim that you checked a live record; be transparent when context is insufficient."


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int, model_metadata: dict[str, Any], usage_reported: bool) -> tuple[float | None, str]:
    if not usage_reported:
        return None, "usage_unreported"
    pricing = model_metadata.get("pricing")
    source = model_metadata.get("price_source", "unpriced")
    if not isinstance(pricing, dict):
        pricing, source = get_model_pricing(model_id)
    if not pricing:
        return None, "unpriced"
    cost = (input_tokens * float(pricing.get("input_per_1m", 0)) + output_tokens * float(pricing.get("output_per_1m", 0))) / 1_000_000
    return round(cost, 10), source


def run_benchmark(run_id: str) -> None:
    """Execute each model/workflow/case combination and persist results incrementally."""
    with connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            return
        config = decode_json(run["config_json"], {})
        dataset_snapshot = config.get("dataset_snapshot", {})
        cases = dataset_snapshot.get("cases", [])
        model_ids = decode_json(run["model_ids_json"], [])
        workflow_ids = config.get("workflow_ids") or (["tool_agent"] if config.get("enable_tools", True) else ["direct"])
        conn.execute("UPDATE runs SET status='running', started_at=? WHERE id=?", (utc_now(), run_id))

    failed = 0
    try:
        for model_id in model_ids:
            model_meta = get_model(model_id)
            provider = get_provider(model_meta["provider"])
            for workflow_id in workflow_ids:
                enable_tools = workflow_id == "tool_agent"
                system_prompt = SYSTEM_PROMPT if enable_tools else DIRECT_SYSTEM_PROMPT
                for case in cases:
                    prompt_parts = []
                    if case.get("context"):
                        prompt_parts.append("AUTHORITATIVE CONTEXT:\n" + str(case["context"]))
                    prompt_parts.append("TASK:\n" + str(case["prompt"]))
                    prompt = "\n\n".join(prompt_parts)
                    started = time.perf_counter()
                    try:
                        result = provider.generate(model_id, system_prompt, prompt, enable_tools=enable_tools)
                        latency_ms = round((time.perf_counter() - started) * 1000, 2)
                        evidence_material = "\n".join(json.dumps(call.get("result", {}), ensure_ascii=False) for call in result.tool_calls)
                        scores = evaluate_case(case, result.text, result.tool_calls, evidence_material)
                        cost, cost_source = _estimate_cost(model_id, result.input_tokens, result.output_tokens, model_meta, result.usage_reported)
                        _insert_result({
                            "run_id": run_id,
                            "case": case,
                            "model_id": model_id,
                            "provider": model_meta["provider"],
                            "workflow_id": workflow_id,
                            "status": "completed",
                            "response": result.text,
                            "latency_ms": latency_ms,
                            "input_tokens": result.input_tokens,
                            "output_tokens": result.output_tokens,
                            "usage_reported": result.usage_reported,
                            "cost_usd": cost,
                            "cost_source": cost_source,
                            "scores": scores,
                            "tool_calls": result.tool_calls,
                            "source_material": f"{case.get('context', '')}\n{evidence_material}",
                            "error": None,
                        })
                    except Exception as exc:  # Persist per-case failures and continue other candidates.
                        latency_ms = round((time.perf_counter() - started) * 1000, 2)
                        safe_error = str(exc)[:600]
                        error_kind = "provider_error" if isinstance(exc, ProviderError) else "execution_error"
                        failure_analysis = [{"type": error_kind, "message": safe_error}]
                        _insert_result({
                            "run_id": run_id,
                            "case": case,
                            "model_id": model_id,
                            "provider": model_meta["provider"],
                            "workflow_id": workflow_id,
                            "status": "failed",
                            "response": "",
                            "latency_ms": latency_ms,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "usage_reported": False,
                            "cost_usd": None,
                            "cost_source": "unpriced",
                            "scores": {"accuracy_score": None, "grounding_score": None, "tool_reliability_score": None, "failure_analysis": failure_analysis},
                            "tool_calls": [],
                            "source_material": str(case.get("context", "")),
                            "error": safe_error,
                        })
                        failed += 1
        final_status = "completed_with_errors" if failed else "completed"
        with connect() as conn:
            conn.execute("UPDATE runs SET status=?, finished_at=? WHERE id=?", (final_status, utc_now(), run_id))
    except Exception as exc:
        with connect() as conn:
            conn.execute("UPDATE runs SET status='failed', finished_at=?, error=? WHERE id=?", (utc_now(), str(exc)[:600], run_id))


def _insert_result(row: dict[str, Any]) -> None:
    scores = row.get("scores") or {}
    with connect() as conn:
        conn.execute(
            """INSERT INTO results (
              run_id,case_id,case_title,case_category,model_id,provider,workflow_id,status,response,latency_ms,
              input_tokens,output_tokens,usage_reported,cost_usd,cost_source,accuracy_score,grounding_score,
              tool_reliability_score,failure_analysis_json,tool_calls_json,source_material,error,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["run_id"], row["case"].get("id", "unknown"), row["case"].get("title", "Untitled case"),
                row["case"].get("category", "general"), row["model_id"], row["provider"], row.get("workflow_id", "tool_agent"), row["status"],
                row.get("response", ""), row.get("latency_ms"), row.get("input_tokens", 0), row.get("output_tokens", 0),
                int(bool(row.get("usage_reported", False))), row.get("cost_usd"), row.get("cost_source", "unpriced"), scores.get("accuracy_score"),
                scores.get("grounding_score"), scores.get("tool_reliability_score"),
                json.dumps(scores.get("failure_analysis", []), ensure_ascii=False), json.dumps(row.get("tool_calls", []), ensure_ascii=False),
                row.get("source_material", ""), row.get("error"), utc_now(),
            ),
        )
