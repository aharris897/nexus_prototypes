"""Pump matching: find where the system curve intersects a pump curve.

The "design point" or "operating point" of a lift station is the flow rate
at which:

    pump_head_ft(Q) == TDH_system_ft(Q)

This module finds that intersection numerically, evaluates how good the
match is (efficiency and NPSH at that point if available), and provides a
helper to pick the best-fitting pump from a catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import brentq

from ..catalog.pump_curves import PumpCurve
from .head_loss import TDHCurve, build_tdh_curve
from ..models import ForceMainSegment


@dataclass(frozen=True)
class OperatingPoint:
    """The intersection of a pump curve with a system curve."""

    pump_model: str
    is_placeholder: bool
    flow_gpm: float
    head_ft: float
    efficiency_pct: float | None
    npshr_ft: float | None
    #: True if the operating point lies within the pump's published range.
    in_curve_range: bool
    #: Distance (in GPM) from the design pumping rate target. Useful for
    #: ranking candidate pumps.
    gpm_offset_from_target: float | None = None


def find_operating_point(
    pump: PumpCurve,
    system_curve: TDHCurve,
    target_design_gpm: float | None = None,
) -> OperatingPoint:
    """Find where pump and system curves intersect.

    Strategy:
      1. Sample both curves at the system curve's flow points.
      2. Find the bracket where pump_head - system_head changes sign.
      3. Use Brent's method to find the precise intersection.

    Args:
        pump: A PumpCurve.
        system_curve: A pre-built TDHCurve.
        target_design_gpm: Optional. If given, the result includes the
            offset from this target so candidates can be ranked.

    Returns:
        An OperatingPoint. If the pump curve doesn't intersect the system
        curve in range, head_ft will be NaN and in_curve_range=False.
    """
    flows = system_curve.flows_gpm()
    sys_heads = system_curve.tdh_ft()

    def diff(q: float) -> float:
        ph = pump.head_at(q)
        # Need to interpolate system curve at q too; use linear interp
        # (system curve is dense and monotonic so this is fine).
        # Find bracket
        for i in range(len(flows) - 1):
            if flows[i] <= q <= flows[i + 1]:
                t = (q - flows[i]) / (flows[i + 1] - flows[i])
                sh = sys_heads[i] + t * (sys_heads[i + 1] - sys_heads[i])
                return ph - sh
        return float("nan")

    # Walk the curve to find a sign change in (pump - system).
    q_low = max(pump.flow_min_gpm, flows[0])
    q_high = min(pump.flow_max_gpm, flows[-1])
    if q_high <= q_low:
        return OperatingPoint(
            pump_model=pump.model,
            is_placeholder=pump.is_placeholder,
            flow_gpm=float("nan"),
            head_ft=float("nan"),
            efficiency_pct=None,
            npshr_ft=None,
            in_curve_range=False,
            gpm_offset_from_target=None,
        )

    # Sample inside the overlap
    n_samples = 50
    step = (q_high - q_low) / n_samples
    prev_q = q_low
    prev_d = diff(prev_q)
    found = False
    op_q = float("nan")

    for i in range(1, n_samples + 1):
        q = q_low + i * step
        d = diff(q)
        if not (prev_d != prev_d):  # not NaN
            if (prev_d >= 0 and d <= 0) or (prev_d <= 0 and d >= 0):
                if prev_d != d:
                    op_q = brentq(diff, prev_q, q)
                else:
                    op_q = (prev_q + q) / 2.0
                found = True
                break
        prev_q = q
        prev_d = d

    if not found:
        return OperatingPoint(
            pump_model=pump.model,
            is_placeholder=pump.is_placeholder,
            flow_gpm=float("nan"),
            head_ft=float("nan"),
            efficiency_pct=None,
            npshr_ft=None,
            in_curve_range=False,
            gpm_offset_from_target=None,
        )

    op_h = pump.head_at(op_q)
    eff = pump.efficiency_at(op_q)
    npshr = pump.npshr_at(op_q)
    offset = (op_q - target_design_gpm) if target_design_gpm is not None else None

    return OperatingPoint(
        pump_model=pump.model,
        is_placeholder=pump.is_placeholder,
        flow_gpm=op_q,
        head_ft=op_h,
        efficiency_pct=eff,
        npshr_ft=npshr,
        in_curve_range=True,
        gpm_offset_from_target=offset,
    )


def rank_pumps(
    pumps: list[PumpCurve],
    system_curve: TDHCurve,
    target_design_gpm: float,
) -> list[OperatingPoint]:
    """Score and rank candidate pumps against a target design point.

    Pumps are sorted by absolute distance from the target GPM. Pumps whose
    curves don't intersect the system curve in range are placed at the end.
    """
    results = [
        find_operating_point(p, system_curve, target_design_gpm) for p in pumps
    ]

    def sort_key(op: OperatingPoint) -> tuple[int, float]:
        if not op.in_curve_range or op.gpm_offset_from_target is None:
            return (1, 0.0)
        return (0, abs(op.gpm_offset_from_target))

    return sorted(results, key=sort_key)


__all__ = [
    "OperatingPoint",
    "find_operating_point",
    "rank_pumps",
]


def _unused_import_keepers() -> None:  # pragma: no cover
    """Force imports of helper symbols used only in type hints / examples."""
    _ = build_tdh_curve, ForceMainSegment
