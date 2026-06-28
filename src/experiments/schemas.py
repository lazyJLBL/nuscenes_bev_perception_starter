"""Shared schemas for offline model-comparison experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ExperimentSpec:
    """Decision-complete input for one nuScenes-only offline experiment."""

    perception_model: str = "pointpillars"
    decision_model: str = "fsm_decision"
    planning_model: str = "mpc_smoothing"
    preprocessing_model: str = "lidar_topdown"
    dataset_version: str = "v1.0-mini"
    split: str = "mini_val"
    max_samples: int = 8
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentSpec":
        aliases = {
            "perception": "perception_model",
            "decision": "decision_model",
            "planning": "planning_model",
            "preprocessing": "preprocessing_model",
        }
        normalized = {}
        for key, value in data.items():
            normalized[aliases.get(key, key)] = value
        return cls(**{k: v for k, v in normalized.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricReport:
    """Metrics for one subsystem in an experiment."""

    subsystem: str
    model_id: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    summary: str = ""
    artifacts: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunRecord:
    """Persisted result for one offline experiment run."""

    run_id: str
    created_at: str
    spec: ExperimentSpec
    reports: Dict[str, MetricReport]
    status: str = "ok"
    output_dir: Optional[str] = None
    timesteps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["spec"] = self.spec.to_dict()
        data["reports"] = {k: v.to_dict() for k, v in self.reports.items()}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        spec = ExperimentSpec.from_dict(data.get("spec", {}))
        reports = {
            key: MetricReport(**value)
            for key, value in data.get("reports", {}).items()
        }
        return cls(
            run_id=data["run_id"],
            created_at=data.get("created_at", utc_now_iso()),
            spec=spec,
            reports=reports,
            status=data.get("status", "ok"),
            output_dir=data.get("output_dir"),
            timesteps=data.get("timesteps", []),
        )
