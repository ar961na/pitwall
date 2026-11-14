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
