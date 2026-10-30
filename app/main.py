from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles

from app.config import DEFAULT_PRICING, get_model_pricing
from app.database import connect, decode_json, init_db, new_id, seed_datasets, utc_now
from app.providers.registry import PROVIDER_META, get_model, list_models, provider_configured
from app.schemas import DatasetCreate, DatasetUpdate, RunCreate
from app.services.benchmark import run_benchmark
from app.services.evaluation import EVALUATOR_VERSION, aggregate_run_summary

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_datasets()
    # BackgroundTasks run in-process. Mark work interrupted by a server restart
    # instead of leaving a run indefinitely in a queued/running state.
    with connect() as conn:
        conn.execute(
            "UPDATE runs SET status='failed', finished_at=?, error=? WHERE status IN ('queued','running')",
            (utc_now(), 'Run interrupted because the ProofBench process restarted. Re-run the benchmark to resume with a fresh run ID.'),
        )
    yield


app = FastAPI(
    title="ProofBench API",
    description="Reproducible LLM and tool-using agent benchmarks with explainable rubric scores.",
    version="1.0.0",
    lifespan=lifespan,
)


def _dataset_payload(row: sqlite3.Row) -> dict[str, Any]:
    cases = decode_json(row["cases_json"], [])
    return {
        "id": row["id"], "name": row["name"], "description": row["description"], "category": row["category"],
        "cases": cases, "case_count": len(cases), "version": row["version"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def _result_payload(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["failure_analysis"] = decode_json(item.pop("failure_analysis_json", None), [])
    item["tool_calls"] = decode_json(item.pop("tool_calls_json", None), [])
    item["usage_reported"] = bool(item.get("usage_reported", 0))
    return item


def _get_results(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM results WHERE run_id=? ORDER BY id ASC", (run_id,)).fetchall()
    return [_result_payload(row) for row in rows]


def _run_payload(row: sqlite3.Row, include_results: bool = False) -> dict[str, Any]:
    run = dict(row)
    model_ids = decode_json(run.pop("model_ids_json", None), [])
    config = decode_json(run.pop("config_json", None), {})
    results = _get_results(run["id"])
    summaries = aggregate_run_summary(results)
    run.update({
        "model_ids": model_ids,
        "model_count": len(model_ids),
        "workflow_ids": config.get("workflow_ids") or (["tool_agent"] if config.get("enable_tools", True) else ["direct"]),
        "workflow_count": len(config.get("workflow_ids") or (["tool_agent"] if config.get("enable_tools", True) else ["direct"])),
        "candidate_count": len(model_ids) * len(config.get("workflow_ids") or (["tool_agent"] if config.get("enable_tools", True) else ["direct"])),
        "config": {k: v for k, v in config.items() if k not in {"dataset_snapshot", "model_catalog_snapshot"}},
        "dataset_version": config.get("dataset_snapshot", {}).get("version"),
        "case_count": len(config.get("dataset_snapshot", {}).get("cases", [])),
        "result_count": len(results),
        "completed_result_count": sum(1 for r in results if r["status"] == "completed"),
        "failed_result_count": sum(1 for r in results if r["status"] != "completed"),
        "model_summaries": summaries,
    })
    if include_results:
        run["dataset_snapshot"] = config.get("dataset_snapshot", {})
        run["model_catalog_snapshot"] = config.get("model_catalog_snapshot", [])
        run["results"] = results

        run["recommendation"] = None

        if run.get("status") in {"completed", "completed_with_errors"}:
            eligible = []

            for candidate in summaries:
                case_count = int(candidate.get("case_count") or 0)
                completed_cases = int(candidate.get("completed_cases") or 0)

                # Require at least 3 cases and 80% successful completion.
                minimum_completed = max(3, (4 * case_count + 4) // 5)

                if (
                    case_count >= 3
                    and completed_cases >= minimum_completed
                    and candidate.get("composite_score") is not None
                ):
                    eligible.append(candidate)

            eligible.sort(
                key=lambda candidate: float(candidate["composite_score"]),
                reverse=True
            )

            if eligible:
                best = eligible[0]
                runner_up = eligible[1] if len(eligible) > 1 else None

                delta = (
                    best["composite_score"] - runner_up["composite_score"]
                    if runner_up else None
                )

                run["recommendation"] = {
                    "model_id": best["model_id"],
                    "workflow_id": best["workflow_id"],
                    "composite_score": best["composite_score"],
                    "score_delta": round(delta, 2) if delta is not None else None,
                    "reason": (
                        f"Highest composite score among candidates meeting "
                        f"the evidence threshold "
                        f"({best['completed_cases']}/{best['case_count']} cases completed)."
                    ),
                    "caveat": (
                        "Use this as evidence for a targeted pilot, not as a "
                        "universal model ranking. Validate with representative "
                        "tasks and current pricing."
                    ),
                }
    return run


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "proofbench", "version": app.version, "evaluator_version": EVALUATOR_VERSION}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    with connect() as conn:
        dataset_count = conn.execute("SELECT COUNT(*) AS n FROM datasets").fetchone()["n"]
        run_count = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        completed_run_count = conn.execute("SELECT COUNT(*) AS n FROM runs WHERE status IN ('completed','completed_with_errors')").fetchone()["n"]
        evaluated_models = conn.execute("SELECT COUNT(DISTINCT model_id) AS n FROM results WHERE status='completed'").fetchone()["n"]
        results_rows = conn.execute("SELECT * FROM results WHERE status='completed'").fetchall()
        recent_rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 6").fetchall()
    all_results = [_result_payload(r) for r in results_rows]
    metric_values = [r["accuracy_score"] for r in all_results if r["accuracy_score"] is not None]
    mean_accuracy = round(sum(metric_values) / len(metric_values), 2) if metric_values else None
    # Leaderboard groups all historical results by model. Costs across runs are
    # descriptive, while efficiency scores are recomputed inside each individual run.
    all_candidates: dict[str, list[dict[str, Any]]] = {}
    for result in all_results:
        candidate_id = f"{result.get('workflow_id', 'tool_agent')}::{result['model_id']}"
        all_candidates.setdefault(candidate_id, []).append(result)
    global_leaderboard = []
    for candidate_id, rows in all_candidates.items():
        summary = aggregate_run_summary(rows)[0] if rows else {}
        summary["candidate_id"] = candidate_id
        summary["cross_run_note"] = "Cross-run results summarize historical accuracy; compare candidates on the same run for fairer operational ranking."
        global_leaderboard.append(summary)
    global_leaderboard.sort(key=lambda s: (s.get("accuracy") is None, -(s.get("accuracy") or 0)))
    return {
        "stats": {
            "total_runs": run_count,
            "completed_runs": completed_run_count,
            "datasets": dataset_count,
            "evaluated_models": evaluated_models,
            "average_accuracy": mean_accuracy,
            "case_evaluations": len(all_results),
        },
        "recent_runs": [_run_payload(r) for r in recent_rows],
        "leaderboard": global_leaderboard[:6],
        "providers": _provider_status(),
    }


def _provider_status() -> list[dict[str, Any]]:
    return [
        {"id": provider_id, "label": meta["label"], "configured": provider_configured(provider_id), "description": meta["description"], "env_key": meta["env_key"]}
        for provider_id, meta in PROVIDER_META.items()
    ]


@app.get("/api/models")
def models() -> dict[str, Any]:
    catalog = list_models()
    return {"models": catalog, "providers": _provider_status()}


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    pricing_rows = []
    known = {m["id"] for m in list_models()}
    for model_id in sorted(known):
        pricing, source = get_model_pricing(model_id)
        pricing_rows.append({"model_id": model_id, "pricing": pricing, "source": source})
    return {
        "providers": _provider_status(),
        "pricing": pricing_rows,
        "bundled_rate_card_is_illustrative": True,
        "evaluator_version": EVALUATOR_VERSION,
        "database_path": "configured on server; not exposed to browser",
    }


@app.get("/api/datasets")
def list_datasets() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM datasets ORDER BY created_at ASC").fetchall()
    return {"datasets": [_dataset_payload(row) for row in rows]}


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return _dataset_payload(row)


@app.post("/api/datasets", status_code=201)
def create_dataset(payload: DatasetCreate) -> dict[str, Any]:
    now = utc_now()
    dataset_id = new_id("ds")
    cases = [case.model_dump() for case in payload.cases]
    if len({case["id"] for case in cases}) != len(cases):
        raise HTTPException(status_code=422, detail="Each case must have a unique id within the dataset.")
    with connect() as conn:
        conn.execute(
            "INSERT INTO datasets (id,name,description,category,cases_json,version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (dataset_id, payload.name.strip(), payload.description.strip(), payload.category.strip(), json.dumps(cases, ensure_ascii=False), 1, now, now),
        )
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    return _dataset_payload(row)


@app.put("/api/datasets/{dataset_id}")
def update_dataset(dataset_id: str, payload: DatasetUpdate) -> dict[str, Any]:
    cases = [case.model_dump() for case in payload.cases]
    if len({case["id"] for case in cases}) != len(cases):
        raise HTTPException(status_code=422, detail="Each case must have a unique id within the dataset.")
    now = utc_now()
    with connect() as conn:
        previous = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        if not previous:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        conn.execute(
            "UPDATE datasets SET name=?,description=?,category=?,cases_json=?,version=version+1,updated_at=? WHERE id=?",
            (payload.name.strip(), payload.description.strip(), payload.category.strip(), json.dumps(cases, ensure_ascii=False), now, dataset_id),
        )
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    return _dataset_payload(row)


@app.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str) -> Response:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dataset not found.")
    return Response(status_code=204)


@app.get("/api/runs")
def list_runs(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    with connect() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return {"runs": [_run_payload(row) for row in rows]}


@app.post("/api/runs", status_code=202)
def create_run(payload: RunCreate, background_tasks: BackgroundTasks) -> dict[str, Any]:
    with connect() as conn:
        dataset_row = conn.execute("SELECT * FROM datasets WHERE id=?", (payload.dataset_id,)).fetchone()
    if not dataset_row:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if len(payload.model_ids) > 8:
        raise HTTPException(status_code=422, detail="A benchmark can compare up to 8 models at once.")

    catalog: list[dict[str, Any]] = []
    for model_id in payload.model_ids:
        try:
            model = get_model(model_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not model["configured"]:
            label = model["provider_label"]
            raise HTTPException(status_code=400, detail=f"{label} is not configured for {model_id}. Add the provider environment variable and restart ProofBench.")
        catalog.append(model)

    dataset = _dataset_payload(dataset_row)
    name = ((payload.name or '').strip() or f"{dataset['name']} · {', '.join(payload.model_ids)}")[:120]
    run_id = new_id("run")
    config = {
        "dataset_snapshot": {
            "id": dataset["id"], "name": dataset["name"], "version": dataset["version"],
            "category": dataset["category"], "cases": dataset["cases"],
        },
        "model_catalog_snapshot": catalog,
        "workflow_ids": payload.workflow_ids,
        "temperature": 0,
        "evaluator_version": EVALUATOR_VERSION,
    }
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "INSERT INTO runs (id,name,dataset_id,dataset_name,status,model_ids_json,config_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, name, payload.dataset_id, dataset["name"], "queued", json.dumps(payload.model_ids), json.dumps(config, ensure_ascii=False), now),
        )
    background_tasks.add_task(run_benchmark, run_id)
    return {"id": run_id, "name": name, "status": "queued", "created_at": now, "message": "Benchmark queued. Poll the run detail endpoint for progress and results."}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")
    return _run_payload(row, include_results=True)


@app.get("/api/methodology")
def methodology() -> dict[str, Any]:
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "metrics": [
            {"id": "accuracy", "label": "Task accuracy", "definition": "Configured required-phrase coverage, with a penalty for forbidden phrases; token F1 against a reference is used when no required phrases are configured.", "caveat": "Rubric-based, not a semantic judge. Rubrics must reflect the task's true success criteria."},
            {"id": "grounding", "label": "Grounding", "definition": "Coverage of configured evidence anchors that appear in supplied context or observed tool outputs and are reflected in the answer.", "caveat": "Lexical evidence-anchor coverage, not entailment or a complete hallucination detector."},
            {"id": "tool_reliability", "label": "Tool reliability", "definition": "F1 of expected versus observed tool names multiplied by the successful local-tool execution rate.", "caveat": "The included registry is local and deterministic. Replace tools with approved business integrations for workflow-specific evaluation."},
            {"id": "latency", "label": "Latency", "definition": "Wall-clock elapsed milliseconds around each provider invocation, including tool rounds and network time.", "caveat": "Affected by provider load, network, region, and run order. Repeat and randomize runs for stronger comparisons."},
            {"id": "cost", "label": "Estimated cost", "definition": "Observed provider token usage multiplied by configured per-million-token prices.", "caveat": "Bundled prices are illustrative estimates. Set current rates with PROOFBENCH_MODEL_PRICING_JSON before making budget decisions; token usage may vary by provider."},
        ],
        "composite_weights": {"accuracy": 0.40, "grounding": 0.30, "tool_reliability": 0.20, "latency_efficiency": 0.05, "cost_efficiency": 0.05},
        "composite_note": "Weights are renormalized when a metric is not applicable, then the weighted score is discounted by the model's failed-case rate. Latency and cost efficiency are normalized against other models in the same run. Use the composite as a decision aid, not a universal ranking.",
    }


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="frontend")
