"""Validation helpers for detection predictions, metrics, and run records."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    prediction_count: int = 0


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def count_nuscenes_predictions(prediction_file: str) -> int:
    data = _load_json(prediction_file)
    results = data.get("results")
    if not isinstance(results, dict):
        return 0
    return sum(len(v) for v in results.values() if isinstance(v, list))


def validate_detection_outputs(
    prediction_file: Optional[str],
    metrics_file: Optional[str],
    run_record_file: Optional[str] = None,
    require_positive_metrics: bool = True,
) -> ValidationResult:
    """Validate that a detection experiment produced useful, comparable outputs."""

    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {}
    prediction_count = 0

    if not prediction_file or not os.path.exists(prediction_file):
        errors.append(f"prediction file missing: {prediction_file}")
    else:
        try:
            prediction_count = count_nuscenes_predictions(prediction_file)
            if prediction_count == 0:
                errors.append("prediction file contains zero detections")
        except Exception as exc:
            errors.append(f"prediction file is unreadable: {exc}")

    if not metrics_file or not os.path.exists(metrics_file):
        errors.append(f"metrics file missing: {metrics_file}")
    else:
        try:
            metrics = _load_json(metrics_file)
            for key in ("mean_ap", "nd_score"):
                value = metrics.get(key)
                if not _is_finite_number(value):
                    errors.append(f"metrics field {key!r} is missing or not finite")
            if require_positive_metrics:
                mean_ap = float(metrics.get("mean_ap", 0.0) or 0.0)
                nds = float(metrics.get("nd_score", 0.0) or 0.0)
                if mean_ap <= 0.0 and nds <= 0.0:
                    errors.append("mean_ap and nd_score are both zero; result is not a useful benchmark")
        except Exception as exc:
            errors.append(f"metrics file is unreadable: {exc}")

    if run_record_file is not None:
        if not os.path.exists(run_record_file):
            errors.append(f"experiment run record missing: {run_record_file}")
        else:
            try:
                run_record = _load_json(run_record_file)
                if "spec" not in run_record or "reports" not in run_record:
                    errors.append("run record is missing spec or reports")
            except Exception as exc:
                errors.append(f"run record is unreadable: {exc}")

    return ValidationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
        prediction_count=prediction_count,
    )
