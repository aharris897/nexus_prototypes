"""JSON output renderer for DesignReport.

Serializes a complete DesignReport to a JSON-friendly dict structure.
Useful as the wire format for the FastAPI layer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

from ..calc.design import DesignReport


def _to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses, enums, and lists to plain dicts/lists.

    Handles NaN by converting to None (JSON doesn't support NaN by default).
    """
    if obj is None:
        return None
    if isinstance(obj, float):
        if obj != obj:  # NaN check
            return None
        return obj
    if isinstance(obj, (int, str, bool)):
        return obj
    if hasattr(obj, "value") and hasattr(obj, "name"):
        # Enum
        return obj.value
    if is_dataclass(obj):
        return {f.name: _to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    return str(obj)


def report_to_dict(report: DesignReport) -> dict:
    """Convert a DesignReport to a plain dict.

    The result is JSON-serializable and round-trips cleanly through
    json.dumps / json.loads. NaN values become null.

    Note: PumpCurve internal interpolator state is not serialized.
    """
    # Manually construct the dict to skip non-data attrs like interpolators
    out: dict = {}
    out["project"] = _to_dict(report.project)
    out["flow_estimate"] = _to_dict(report.flow_estimate)
    out["pumping_flow"] = _to_dict(report.pumping_flow)
    out["static_head"] = _to_dict(report.static_head)
    if report.tdh_curve is not None:
        out["tdh_curve"] = {
            "static_head_ft": report.tdh_curve.static_head_ft,
            "segments": [_to_dict(s) for s in report.tdh_curve.segments],
            "points": [
                {
                    "flow_gpm": p.flow_gpm,
                    "total_dynamic_head_ft": p.total_dynamic_head_ft,
                    "segments": [_to_dict(s) for s in p.segment_losses],
                }
                for p in report.tdh_curve.points
            ],
        }
    else:
        out["tdh_curve"] = None
    out["wet_well_volume"] = _to_dict(report.wet_well_volume)
    out["cycle_times"] = _to_dict(report.cycle_times)
    out["operating_point"] = _to_dict(report.operating_point)
    if report.selected_pump is not None:
        out["selected_pump"] = {
            "manufacturer": report.selected_pump.manufacturer,
            "model": report.selected_pump.model,
            "impeller_code": report.selected_pump.impeller_code,
            "speed_rpm": report.selected_pump.speed_rpm,
            "is_placeholder": report.selected_pump.is_placeholder,
            "points": [
                {
                    "flow_gpm": p.flow_gpm,
                    "head_ft": p.head_ft,
                    "efficiency_pct": p.efficiency_pct,
                    "npshr_ft": p.npshr_ft,
                }
                for p in report.selected_pump.points
            ],
        }
    else:
        out["selected_pump"] = None
    out["buoyancy"] = _to_dict(report.buoyancy)
    out["notes"] = list(report.notes)
    return out


def render_json(report: DesignReport, path: Path | str, indent: int = 2) -> Path:
    """Write the report to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(report_to_dict(report), f, indent=indent, default=str)
    return p
