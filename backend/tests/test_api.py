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
    assert all(a["mean_s"] <= b["mean_s"] for a, b in zip(results, results[1:], strict=False))


def test_optimize_rejects_bad_params():
    assert client.post("/api/strategy/optimize", json={"n_sims": 5}).status_code == 422


def test_predict_without_model_is_501():
    assert client.get("/api/predict/2026/1").status_code == 501


def test_sources_lists_attribution():
    body = client.get("/api/sources").json()
    assert {s["tag"] for s in body["sources"]} == {"D1", "D2", "D3"}
    assert "not associated with Formula 1" in body["disclaimer"]
