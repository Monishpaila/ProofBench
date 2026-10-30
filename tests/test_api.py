def test_health_and_seed_datasets(client):
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['status'] == 'ok'
    assert health.json()['evaluator_version'] == 'proofbench-rubric-v1'

    result = client.get('/api/datasets')
    assert result.status_code == 200
    datasets = result.json()['datasets']
    assert len(datasets) >= 2
    support = next(ds for ds in datasets if ds['id'] == 'ds_support_core')
    assert support['case_count'] >= 6
    assert support['cases'][0]['must_include']


def test_create_and_update_dataset_versions(client):
    payload = {
        'name': 'Regression suite',
        'description': 'A local API test dataset.',
        'category': 'qa',
        'cases': [{
            'id': 'qa_01', 'title': 'A simple answer', 'prompt': 'Say approved.',
            'context': 'The state is approved.', 'reference_answer': 'approved',
            'must_include': ['approved'], 'grounding_facts': ['approved'],
            'expected_tools': [], 'must_not_include': [], 'tags': ['test'],
        }],
    }
    created = client.post('/api/datasets', json=payload)
    assert created.status_code == 201
    data = created.json()
    assert data['version'] == 1
    assert data['case_count'] == 1

    updated_payload = {**payload, 'name': 'Regression suite v2'}
    updated = client.put(f"/api/datasets/{data['id']}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()['version'] == 2
    assert updated.json()['name'] == 'Regression suite v2'


def test_duplicate_case_ids_are_rejected(client):
    case = {'id': 'same', 'title': 'X', 'prompt': 'Y'}
    response = client.post('/api/datasets', json={'name': 'Bad dataset', 'cases': [case, case]})
    assert response.status_code == 422
    assert 'unique id' in response.json()['detail']


def test_run_requires_configured_provider(client):
    response = client.post('/api/runs', json={
        'dataset_id': 'ds_support_core', 'model_ids': ['gpt-4o-mini'], 'enable_tools': True,
    })
    assert response.status_code == 400
    assert 'not configured' in response.json()['detail']


def test_settings_do_not_return_secrets(client, monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'super-secret-value')
    result = client.get('/api/settings')
    assert result.status_code == 200
    content = result.text
    assert 'super-secret-value' not in content
    assert result.json()['providers'][0]['configured'] is True


def test_dashboard_empty_state_has_no_fake_benchmark_scores(client):
    result = client.get('/api/dashboard')
    assert result.status_code == 200
    body = result.json()
    assert body['stats']['total_runs'] == 0
    assert body['stats']['average_accuracy'] is None
    assert body['leaderboard'] == []


def test_benchmark_lifecycle_persists_real_schema_results_without_network(client, monkeypatch):
    """Exercise the run coordinator with a fake adapter and no paid API calls."""
    from app.providers.base import ProviderResponse
    from app.providers.openai_provider import OpenAIProvider

    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-used')

    def fake_generate(self, model_id, system, prompt, enable_tools=True):
        return ProviderResponse(
            text='This is a tested answer grounded in the source context.',
            input_tokens=42,
            output_tokens=12,
            usage_reported=True,
            tool_calls=[],
        )

    monkeypatch.setattr(OpenAIProvider, 'generate', fake_generate)
    response = client.post('/api/runs', json={
        'dataset_id': 'ds_grounded_qa', 'model_ids': ['gpt-4o-mini'], 'workflow_ids': ['direct', 'tool_agent'], 'name': 'Test run',
    })
    assert response.status_code == 202
    run_id = response.json()['id']

    detail = client.get(f'/api/runs/{run_id}')
    assert detail.status_code == 200
    run = detail.json()
    assert run['status'] in {'completed', 'completed_with_errors'}
    assert run['dataset_snapshot']['version'] == 1
    assert len(run['results']) == 6
    assert {result['workflow_id'] for result in run['results']} == {'direct', 'tool_agent'}
    assert {summary['workflow_id'] for summary in run['model_summaries']} == {'direct', 'tool_agent'}
    assert all(result['input_tokens'] == 42 for result in run['results'])
    assert all(result['usage_reported'] is True for result in run['results'])
    assert all(result['cost_usd'] is not None for result in run['results'])
    assert run['model_summaries'][0]['model_id'] == 'gpt-4o-mini'


def test_openai_adapter_executes_allowed_tool_and_records_trace(monkeypatch):
    from app.providers.openai_provider import OpenAIProvider

    monkeypatch.setenv('OPENAI_API_KEY', 'unit-test-key')
    replies = iter([
        {
            'usage': {'prompt_tokens': 12, 'completion_tokens': 4},
            'choices': [{'message': {'content': None, 'tool_calls': [{
                'id': 'call_1', 'type': 'function', 'function': {
                    'name': 'lookup_order', 'arguments': '{"order_id":"ORD-2048"}'
                }
            }]}}],
        },
        {
            'usage': {'prompt_tokens': 30, 'completion_tokens': 10},
            'choices': [{'message': {'content': 'Order ORD-2048 is shipped. Estimated delivery is November 2, 2026.'}}],
        },
    ])
    monkeypatch.setattr('app.providers.openai_provider.request_json', lambda *args, **kwargs: next(replies))
    response = OpenAIProvider().generate('gpt-4o-mini', 'system', 'look up ORD-2048', enable_tools=True)
    assert 'shipped' in response.text
    assert response.usage_reported is True
    assert response.input_tokens == 42
    assert response.output_tokens == 14
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]['name'] == 'lookup_order'
    assert response.tool_calls[0]['ok'] is True
    assert response.tool_calls[0]['result']['order']['status'] == 'shipped'


def test_cost_is_unavailable_when_provider_does_not_report_usage():
    from app.services.benchmark import _estimate_cost

    price = {'pricing': {'input_per_1m': 0.15, 'output_per_1m': 0.60}, 'price_source': 'bundled_estimate'}
    cost, source = _estimate_cost('gpt-4o-mini', 0, 0, price, usage_reported=False)
    assert cost is None
    assert source == 'usage_unreported'



def test_recommendation_requires_evidence_and_preserves_workflow(monkeypatch):
    import json
    import sqlite3
    import app.main as main

    # Create a lightweight database row for the run payload.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    config = {
        "workflow_ids": ["direct", "tool_agent"],
        "dataset_snapshot": {
            "version": 1,
            "cases": [{} for _ in range(8)]
        }
    }

    row = conn.execute(
        """
        SELECT
            ? AS id,
            ? AS model_ids_json,
            ? AS config_json,
            ? AS status
        """,
        (
            "test-run",
            json.dumps(["model-a", "model-b"]),
            json.dumps(config),
            "completed_with_errors",
        ),
    ).fetchone()

    # Candidate A scores highly but completes only 6/8 cases.
    # Candidate B completes 7/8 and is eligible.
    summaries = [
        {
            "model_id": "model-a",
            "workflow_id": "tool_agent",
            "case_count": 8,
            "completed_cases": 6,
            "composite_score": 99.0,
        },
        {
            "model_id": "model-b",
            "workflow_id": "direct",
            "case_count": 8,
            "completed_cases": 7,
            "composite_score": 82.0,
        },
    ]

    monkeypatch.setattr(main, "_get_results", lambda run_id: [])
    monkeypatch.setattr(
        main,
        "aggregate_run_summary",
        lambda results: summaries,
    )

    run = main._run_payload(row, include_results=True)

    # The lower-scoring but sufficiently tested candidate should win.
    assert run["recommendation"]["model_id"] == "model-b"
    assert run["recommendation"]["workflow_id"] == "direct"

    # If no candidate meets the evidence threshold,
    # ProofBench must not produce a recommendation.
    summaries[1]["completed_cases"] = 6

    run = main._run_payload(row, include_results=True)

    assert run["recommendation"] is None

    conn.close()
