from itertools import pairwise

from fastapi.testclient import TestClient

from pitwall.api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_strategy_defaults_roundtrip():
    params = client.get("/api/strategy/defaults").json()
    assert params["total_laps"] == 57 and "SOFT" in params["compounds"]


def test_optimize():
    r = client.post("/api/strategy/optimize", json={"n_sims": 200, "max_stops": 2})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results[0]["gap_s"] == 0
    assert len(results[0]["clean_lap_times_s"]) == 57
    assert all(r["reactive_gain_s"] >= -0.5 for r in results)
    assert all(a["mean_s"] <= b["mean_s"] for a, b in pairwise(results))


def test_optimize_rejects_bad_params():
    assert client.post("/api/strategy/optimize", json={"n_sims": 5}).status_code == 422


def test_predict_without_model_is_503(monkeypatch, tmp_path):
    from pitwall.predict import service

    monkeypatch.setattr(service, "MODEL_PATH", tmp_path / "missing.joblib")
    r = client.get("/api/predict/2026/1")
    assert r.status_code == 503
    assert "train" in r.json()["detail"].lower()


def test_sources_lists_attribution():
    body = client.get("/api/sources").json()
    assert {s["tag"] for s in body["sources"]} == {"D1", "D2", "D3"}
    assert "not associated with Formula 1" in body["disclaimer"]


def test_optimize_reactive_ranks_with_the_policy():
    body = {"n_sims": 300, "params": {"sc_prob_per_lap": 0.05}}
    fixed = client.post("/api/strategy/optimize", json=body).json()
    reactive = client.post("/api/strategy/optimize", json={**body, "reactive": True}).json()
    assert reactive["reactive"] is True and fixed["reactive"] is False
    # with frequent safety cars, reacting makes the best strategy faster on average
    assert reactive["results"][0]["mean_s"] < fixed["results"][0]["mean_s"]


def test_pace_model_without_file_is_503(monkeypatch, tmp_path):
    from pitwall.config import settings

    monkeypatch.setattr(settings, "models_dir", tmp_path)
    r = client.get("/api/sessions/1/pace-model")
    assert r.status_code == 503
    assert "train-pace" in r.json()["detail"]
