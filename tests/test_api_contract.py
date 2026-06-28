from fastapi.testclient import TestClient

import backend.api.routes as routes
from backend.main import app
from src.experiments.schemas import ExperimentSpec, MetricReport, RunRecord, utc_now_iso


def test_modules_expose_real_availability_contract():
    client = TestClient(app)
    response = client.get("/api/modules")

    assert response.status_code == 200
    data = response.json()
    perception_models = data["perception"]["modelsBySub"]["3d_detection"]
    centerpoint = next(model for model in perception_models if model["id"] == "centerpoint")
    assert centerpoint["status"] == "unavailable"
    assert centerpoint["isReal"] is True


def test_run_experiment_endpoint_returns_scorecard(monkeypatch):
    def fake_run(spec):
        return RunRecord(
            run_id="test_run",
            created_at=utc_now_iso(),
            spec=ExperimentSpec.from_dict(spec.to_dict()),
            reports={
                "perception": MetricReport(
                    subsystem="perception",
                    model_id=spec.perception_model,
                    metrics={"latency_ms": 10.0, "mean_ap": 0.1, "nd_score": 0.2},
                ),
                "decision": MetricReport(
                    subsystem="decision",
                    model_id=spec.decision_model,
                    metrics={"latency_ms": 1.0, "safety_rate": 1.0, "avg_target_speed": 8.0},
                ),
                "planning": MetricReport(
                    subsystem="planning",
                    model_id=spec.planning_model,
                    metrics={"latency_ms": 2.0, "jerk": 0.1, "collision_rate": 0.0, "offroad_rate": 0.0},
                ),
            },
            timesteps=[{"step": 0, "time": 0.0, "x": 0.0, "y": 0.0}],
        )

    monkeypatch.setattr(routes, "run_offline_experiment", fake_run)
    client = TestClient(app)
    response = client.post(
        "/api/run_experiment",
        json={
            "preprocessing": "lidar_topdown",
            "perception": "pointpillars",
            "decision": "fsm_decision",
            "planning": "mpc_smoothing",
            "max_samples": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["stats"]["safety_score"] == 100.0
    assert payload["reports"]["perception"]["metrics"]["nd_score"] == 0.2


def test_health_endpoint_exposes_runtime_capabilities():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["pid"] > 0
    assert payload["routes_path"].endswith("routes.py")
    assert payload["planning_path"].endswith("planning.py")
    assert payload["capabilities"]["visual_obstacles"] is True
    assert payload["capabilities"]["speed_kmh"] is True


def test_experiments_endpoint_lists_recent_records():
    client = TestClient(app)
    response = client.get("/api/experiments?limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "records" in payload
    assert payload["count"] == len(payload["records"])
    assert payload["count"] <= 3


def test_run_sandbox_returns_visual_obstacle_contract(monkeypatch):
    def fake_run(spec):
        return RunRecord(
            run_id="sandbox_run",
            created_at=utc_now_iso(),
            spec=ExperimentSpec.from_dict(spec.to_dict()),
            reports={
                "perception": MetricReport(
                    subsystem="perception",
                    model_id=spec.perception_model,
                    metrics={"latency_ms": 10.0, "mean_ap": 0.1, "nd_score": 0.2},
                ),
                "decision": MetricReport(
                    subsystem="decision",
                    model_id=spec.decision_model,
                    metrics={"latency_ms": 1.0, "safety_rate": 1.0, "avg_target_speed": 8.0},
                ),
                "planning": MetricReport(
                    subsystem="planning",
                    model_id=spec.planning_model,
                    metrics={
                        "latency_ms": 2.0,
                        "jerk": 0.1,
                        "collision_rate": 0.0,
                        "offroad_rate": 0.0,
                        "visual_obstacles": [
                            {
                                "x": 14.0,
                                "y": 1.0,
                                "width": 2.0,
                                "length": 4.0,
                                "safety_buffer": 1.2,
                                "in_view": True,
                                "in_road": True,
                                "edge_hint": "",
                            }
                        ],
                        "visual_scene_score": 21.0,
                        "visual_sample_token": "sample_token",
                        "visual_sample_source": "evaluation_samples",
                    },
                ),
            },
            timesteps=[{"step": 0, "time": 0.0, "x": 0.0, "y": 0.0, "speed_kmh": 12.0, "speed_mps": 3.3}],
        )

    monkeypatch.setattr(routes, "run_offline_experiment", fake_run)
    client = TestClient(app)
    response = client.post("/api/run_sandbox", json={"max_samples": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["obstacle_count"] == 1
    assert len(payload["obstacles"]) == 1
    assert payload["visual_scene_score"] == 21.0
    assert payload["visual_sample_token"] == "sample_token"
    assert payload["visual_sample_source"] == "evaluation_samples"
    assert payload["coordinate_frame"] == {"x": "forward_m", "y": "left_m"}
    assert payload["warnings"] == []
