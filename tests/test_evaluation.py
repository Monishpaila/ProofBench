from app.services.evaluation import aggregate_run_summary, contains_phrase, evaluate_case


def test_phrase_matching_observes_word_boundaries():
    assert contains_phrase("Order is shipped today", "shipped")
    assert not contains_phrase("Order is unshipped today", "shipped")


def test_rubric_scores_accuracy_grounding_and_tool_reliability():
    case = {
        "context": "Refunds are available within 30 days and go to the original payment method.",
        "must_include": ["30 days", "original payment method"],
        "must_not_include": ["instant refund"],
        "grounding_facts": ["30 days", "original payment method"],
        "expected_tools": ["get_policy"],
    }
    calls = [{"name": "get_policy", "ok": True, "result": {"ok": True, "policy": "30 days"}}]
    result = evaluate_case(case, "Refunds are available within 30 days and go to the original payment method.", calls)
    assert result["accuracy_score"] == 100.0
    assert result["grounding_score"] == 100.0
    assert result["tool_reliability_score"] == 100.0
    assert result["failure_analysis"] == []


def test_forbidden_phrase_penalizes_accuracy_and_missing_tool_is_explained():
    case = {
        "context": "Returns are accepted within 30 days.",
        "must_include": ["30 days"],
        "must_not_include": ["free replacement"],
        "grounding_facts": ["30 days"],
        "expected_tools": ["lookup_order"],
    }
    result = evaluate_case(case, "Returns are accepted within 30 days and include a free replacement.", [])
    assert result["accuracy_score"] == 70.0
    assert result["tool_reliability_score"] == 0.0
    assert any(f["type"] == "forbidden_content" for f in result["failure_analysis"])
    assert any(f["type"] == "tool_missing" for f in result["failure_analysis"])


def test_tool_metric_is_not_applicable_when_no_tool_is_expected():
    result = evaluate_case({"context": "Answer yes.", "must_include": ["yes"], "grounding_facts": []}, "Yes.", [])
    assert result["tool_reliability_score"] is None


def test_aggregate_run_score_uses_available_metrics():
    rows = [
        {"model_id": "alpha", "provider": "openai", "status": "completed", "accuracy_score": 90, "grounding_score": 80, "tool_reliability_score": None, "latency_ms": 300, "cost_usd": 0.02, "input_tokens": 100, "output_tokens": 40},
        {"model_id": "beta", "provider": "gemini", "status": "completed", "accuracy_score": 85, "grounding_score": 90, "tool_reliability_score": None, "latency_ms": 150, "cost_usd": 0.01, "input_tokens": 100, "output_tokens": 40},
    ]
    summaries = aggregate_run_summary(rows)
    assert len(summaries) == 2
    assert all(s["composite_score"] is not None for s in summaries)
    assert summaries[0]["model_id"] == "beta"
    assert summaries[0]["latency_efficiency"] == 100.0
    assert summaries[0]["cost_efficiency"] == 100.0


def test_failed_cases_discount_the_composite_score():
    rows = [
        {"model_id": "partial", "workflow_id": "tool_agent", "provider": "openai", "status": "completed", "accuracy_score": 100, "grounding_score": 100, "tool_reliability_score": 100, "latency_ms": 100, "cost_usd": 0.01, "input_tokens": 20, "output_tokens": 10},
        {"model_id": "partial", "workflow_id": "tool_agent", "provider": "openai", "status": "failed", "accuracy_score": None, "grounding_score": None, "tool_reliability_score": None, "latency_ms": 100, "cost_usd": None, "input_tokens": 0, "output_tokens": 0},
    ]
    summary = aggregate_run_summary(rows)[0]
    assert summary['failure_rate'] == 50.0
    assert summary['composite_score'] < 100.0
