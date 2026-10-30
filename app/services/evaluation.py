"""Deterministic, inspectable evaluation metrics for reproducible benchmark runs.

These evaluators intentionally avoid claiming semantic equivalence. They use
rubric phrase checks, evidence-anchor coverage, observed tool calls, and
provider-reported usage; see README for their limitations.
"""
from __future__ import annotations

import re
from typing import Any

EVALUATOR_VERSION = "proofbench-rubric-v1"


def normalize(text: str) -> str:
    text = (text or "").lower().replace("–", "-").replace("—", "-")
    return " ".join(re.findall(r"[a-z0-9$]+", text))


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = f" {normalize(text)} "
    normalized_phrase = normalize(phrase)
    if not normalized_phrase:
        return True
    # Simple boundary-aware matching prevents `shipped` from matching `unshipped`.
    return f" {normalized_phrase} " in normalized_text


def token_f1(prediction: str, reference: str) -> float | None:
    p = set(normalize(prediction).split())
    r = set(normalize(reference).split())
    if not p or not r:
        return None
    overlap = len(p & r)
    precision = overlap / len(p)
    recall = overlap / len(r)
    return (2 * precision * recall / (precision + recall)) * 100 if precision + recall else 0.0


def evaluate_case(
    case: dict[str, Any],
    answer: str,
    tool_calls: list[dict[str, Any]],
    evidence_material: str = "",
) -> dict[str, Any]:
    """Return the three rubric scores and human-readable evidence for one response."""
    failures: list[dict[str, str]] = []
    required = [str(x) for x in case.get("must_include", []) if str(x).strip()]
    forbidden = [str(x) for x in case.get("must_not_include", []) if str(x).strip()]
    required_hits = [item for item in required if contains_phrase(answer, item)]
    missing_required = [item for item in required if item not in required_hits]
    forbidden_hits = [item for item in forbidden if contains_phrase(answer, item)]

    if required:
        accuracy = (len(required_hits) / len(required)) * 100
        # A forbidden phrase incurs a strong, visible penalty. Multiple issues can
        # stack, but the score remains bounded in [0, 100].
        accuracy = max(0.0, accuracy - 30.0 * len(forbidden_hits))
    elif case.get("reference_answer"):
        fallback = token_f1(answer, str(case.get("reference_answer", "")))
        accuracy = fallback
        if fallback is None:
            failures.append({"type": "accuracy", "message": "No usable reference answer or output tokens for rubric scoring."})
    else:
        accuracy = None
        failures.append({"type": "accuracy", "message": "No must_include rubric or reference answer is configured for this case."})

    for item in missing_required:
        failures.append({"type": "missing_requirement", "message": f"Required phrase missing: {item}"})
    for item in forbidden_hits:
        failures.append({"type": "forbidden_content", "message": f"Forbidden phrase present: {item}"})

    # Only count anchor facts explicitly configured for the test case and present
    # in the supplied context or observed local tool outputs. This is intentionally
    # anchor coverage, not an entailment or comprehensive hallucination detector.
    grounding_facts = [str(x) for x in case.get("grounding_facts", []) if str(x).strip()]
    source = f"{case.get('context', '')}\n{evidence_material}"
    verifiable_facts = [fact for fact in grounding_facts if contains_phrase(source, fact)]
    grounded_hits = [fact for fact in verifiable_facts if contains_phrase(answer, fact)]
    if verifiable_facts:
        grounding = 100.0 * len(grounded_hits) / len(verifiable_facts)
    else:
        grounding = None
        if grounding_facts:
            failures.append({"type": "grounding", "message": "No configured grounding anchors were found in the provided context or tool outputs."})
    for fact in verifiable_facts:
        if fact not in grounded_hits:
            failures.append({"type": "grounding_anchor_missing", "message": f"Expected evidence anchor not reflected in answer: {fact}"})

    expected_tools = set(str(x) for x in case.get("expected_tools", []))
    invoked_tools = [str(call.get("name", "")) for call in tool_calls]
    if expected_tools:
        correctly_used = len(expected_tools & set(invoked_tools))
        recall = correctly_used / len(expected_tools)
        successful_count = sum(1 for c in tool_calls if c.get("ok"))
        precision = (correctly_used / len(invoked_tools)) if invoked_tools else 0.0
        # Tool names and successful local execution both matter. Use harmonic mean
        # of expected-tool recall and invocation precision, discounted for tool errors.
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        success_rate = successful_count / len(tool_calls) if tool_calls else 0.0
        tool_reliability = 100.0 * f1 * success_rate
        missed = sorted(expected_tools - set(invoked_tools))
        unexpected = sorted(set(invoked_tools) - expected_tools)
        for tool in missed:
            failures.append({"type": "tool_missing", "message": f"Expected tool was not called: {tool}"})
        for tool in unexpected:
            failures.append({"type": "tool_unexpected", "message": f"Unexpected tool was called: {tool}"})
        for call in tool_calls:
            if not call.get("ok"):
                failures.append({"type": "tool_error", "message": f"Tool {call.get('name', '(unknown)')} failed: {call.get('result', {}).get('error', 'unknown error')}"})
    else:
        tool_reliability = None
        if tool_calls:
            failures.append({"type": "tool_unexpected", "message": "The rubric did not require tools, but the model invoked one or more tools."})

    return {
        "accuracy_score": round(accuracy, 2) if accuracy is not None else None,
        "grounding_score": round(grounding, 2) if grounding is not None else None,
        "tool_reliability_score": round(tool_reliability, 2) if tool_reliability is not None else None,
        "failure_analysis": failures,
        "evidence": {
            "required_hits": required_hits,
            "required_total": len(required),
            "forbidden_hits": forbidden_hits,
            "grounding_hits": grounded_hits,
            "grounding_total": len(verifiable_facts),
            "expected_tools": sorted(expected_tools),
            "invoked_tools": invoked_tools,
        },
    }


def aggregate_model_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate case-level data into model metrics and an explainable score."""
    if not results:
        return {"model_id": None, "case_count": 0, "composite_score": None}

    def average(key: str) -> float | None:
        values = [float(r[key]) for r in results if r.get(key) is not None and r.get("status") == "completed"]
        return round(sum(values) / len(values), 2) if values else None

    completed = [r for r in results if r.get("status") == "completed"]
    latency_values = [float(r["latency_ms"]) for r in completed if r.get("latency_ms") is not None]
    costs = [float(r["cost_usd"]) for r in completed if r.get("cost_usd") is not None]
    total_input = sum(int(r.get("input_tokens") or 0) for r in completed)
    total_output = sum(int(r.get("output_tokens") or 0) for r in completed)
    mean_accuracy = average("accuracy_score")
    mean_grounding = average("grounding_score")
    mean_tools = average("tool_reliability_score")
    mean_latency = round(sum(latency_values) / len(latency_values), 2) if latency_values else None
    total_cost = round(sum(costs), 8) if costs else None
    failure_rate = round(100 * sum(1 for r in results if r.get("status") != "completed") / len(results), 2)

    # Run-local latency and cost scores are assigned by aggregate_run_summary,
    # where candidates are compared against the same benchmark workload.
    return {
        "model_id": results[0].get("model_id"),
        "provider": results[0].get("provider"),
        "workflow_id": results[0].get("workflow_id", "tool_agent"),
        "candidate_id": f"{results[0].get('workflow_id', 'tool_agent')}::{results[0].get('model_id')}",
        "case_count": len(results),
        "completed_cases": len(completed),
        "failure_rate": failure_rate,
        "accuracy": mean_accuracy,
        "grounding": mean_grounding,
        "tool_reliability": mean_tools,
        "mean_latency_ms": mean_latency,
        "total_cost_usd": total_cost,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "composite_score": None,
        "latency_efficiency": None,
        "cost_efficiency": None,
    }


def aggregate_run_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        candidate_id = f"{result.get('workflow_id', 'tool_agent')}::{result.get('model_id', 'unknown')}"
        by_model.setdefault(candidate_id, []).append(result)
    summaries = [aggregate_model_results(rows) for rows in by_model.values()]

    latencies = [s["mean_latency_ms"] for s in summaries if s["mean_latency_ms"] is not None]
    costs = [s["total_cost_usd"] for s in summaries if s["total_cost_usd"] is not None]
    fastest = min(latencies) if latencies else None
    cheapest = min(costs) if costs else None

    for summary in summaries:
        if fastest and summary["mean_latency_ms"] is not None:
            summary["latency_efficiency"] = round(min(100.0, 100 * fastest / max(summary["mean_latency_ms"], 1)), 2)
        if cheapest is not None and summary["total_cost_usd"] is not None:
            # If all candidates cost $0 or usage was zero, the efficiency is not useful.
            summary["cost_efficiency"] = 100.0 if cheapest == 0 and summary["total_cost_usd"] == 0 else (
                round(min(100.0, 100 * cheapest / max(summary["total_cost_usd"], 1e-12)), 2) if cheapest > 0 else 0.0
            )

        components: list[tuple[float, float]] = []
        for key, weight in [("accuracy", 0.40), ("grounding", 0.30), ("tool_reliability", 0.20), ("latency_efficiency", 0.05), ("cost_efficiency", 0.05)]:
            if summary.get(key) is not None:
                components.append((float(summary[key]), weight))
        total_weight = sum(w for _, w in components)
        raw_score = (sum(v * w for v, w in components) / total_weight) if total_weight else None
        # A model should not win by producing a few strong answers while failing many cases.
        summary["composite_score"] = round(raw_score * (1 - float(summary.get("failure_rate") or 0) / 100), 2) if raw_score is not None else None
        summary["score_method"] = "Weighted mean of available metrics, discounted by case failure rate; weights renormalized when a metric is not applicable."

    return sorted(summaries, key=lambda s: (s["composite_score"] is None, -(s["composite_score"] or 0)))
