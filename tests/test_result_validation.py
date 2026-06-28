import json

from src.experiments.result_validation import validate_detection_outputs


def test_detection_validation_rejects_zero_benchmark(tmp_path):
    pred = tmp_path / "predictions.json"
    metrics = tmp_path / "metrics.json"
    run_record = tmp_path / "run_record.json"

    pred.write_text(json.dumps({"results": {"sample": [{"detection_name": "car"}]}}), encoding="utf-8")
    metrics.write_text(json.dumps({"mean_ap": 0.0, "nd_score": 0.0}), encoding="utf-8")
    run_record.write_text(json.dumps({"spec": {}, "reports": {}}), encoding="utf-8")

    result = validate_detection_outputs(str(pred), str(metrics), str(run_record))

    assert not result.ok
    assert any("both zero" in err for err in result.errors)


def test_detection_validation_accepts_positive_metrics(tmp_path):
    pred = tmp_path / "predictions.json"
    metrics = tmp_path / "metrics.json"
    run_record = tmp_path / "run_record.json"

    pred.write_text(json.dumps({"results": {"sample": [{"detection_name": "car"}]}}), encoding="utf-8")
    metrics.write_text(json.dumps({"mean_ap": 0.1, "nd_score": 0.2}), encoding="utf-8")
    run_record.write_text(json.dumps({"spec": {}, "reports": {}}), encoding="utf-8")

    result = validate_detection_outputs(str(pred), str(metrics), str(run_record))

    assert result.ok
    assert result.prediction_count == 1
