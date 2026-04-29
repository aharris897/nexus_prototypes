"""Head loss calculations: friction (Hazen-Williams) and minor (fittings).

Implements steps 4 and 5 of the CMA Order of Operations:
  - Step 4: Tabulate static + dynamic losses for force-main segments.
  - Step 5: Compute TDH = static head + friction loss + fitting loss.

Hazen-Williams head-loss equation in US customary units, as used in the
CMA spreadsheet (TDH!D21):

    hf = 0.002083 * L * (100/C)^1.85 * Q^1.85 / D^4.8655

where:
    hf = friction head loss (ft)
    L  = pipe length (ft)
    C  = Hazen-Williams coefficient (e.g. 120 for ductile iron)
    Q  = flow (GPM)
    D  = inside diameter (inches)

Velocity calc (TDH!B21):
    v (ft/sec) = Q / 448.831 / A
where A = pipe cross-sectional area (sq ft).

Velocity head (TDH!C21):
    hv = v^2 / (2g),  g = 32.2 ft/sec^2

Minor (fitting) loss:
    hL = K * v^2 / (2g)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..constants import (
    GPM_TO_CFS_DIVISOR,
    GRAVITY_FT_S2,
    HAZEN_WILLIAMS_COEFF_US,
    INCHES_PER_FOOT,
    PSI_TO_FT_OF_WATER,
)
from ..models import ForceMainSegment, StaticHeadInputs


# --- Static head ------------------------------------------------------------


@dataclass(frozen=True)
class StaticHeadResult:
    """Static head components and their sum."""

    destination_elevation_ft: float
    pump_off_elevation_ft: float
    static_lift_ft: float
    static_head_at_connection_psi: float
    static_head_at_connection_ft: float
    total_static_head_ft: float


def static_head(inputs: StaticHeadInputs) -> StaticHeadResult:
    """Compute total static head per CMA spreadsheet 'Headloss Fitting' tab.

        static_lift = destination_el - pump_off_el
        static_head_at_conn_ft = psi * 2.31
        total_static = static_lift + static_head_at_conn_ft

    Matches spreadsheet cells D10, D11, D13.
    """
    static_lift = (
        inputs.destination_elevation_ft - inputs.pump_off_elevation_ft
    )
    head_at_conn_ft = (
        inputs.static_head_at_connection_psi * PSI_TO_FT_OF_WATER
    )
    total = static_lift + head_at_conn_ft
    return StaticHeadResult(
        destination_elevation_ft=inputs.destination_elevation_ft,
        pump_off_elevation_ft=inputs.pump_off_elevation_ft,
        static_lift_ft=static_lift,
        static_head_at_connection_psi=inputs.static_head_at_connection_psi,
        static_head_at_connection_ft=head_at_conn_ft,
        total_static_head_ft=total,
    )


# --- Pipe geometry helpers --------------------------------------------------


def pipe_area_ft2(diameter_in: float) -> float:
    """Cross-sectional area of a pipe (ft^2) given inside diameter (in)."""
    d_ft = diameter_in / INCHES_PER_FOOT
    return math.pi * d_ft * d_ft / 4.0


def pipe_velocity_ft_s(flow_gpm: float, diameter_in: float) -> float:
    """Pipe velocity (ft/s) for a given flow (GPM) and diameter (in).

    Matches spreadsheet TDH!B21:
        v = (Q / 448.831) / A
    """
    if flow_gpm == 0.0:
        return 0.0
    return (flow_gpm / GPM_TO_CFS_DIVISOR) / pipe_area_ft2(diameter_in)


def velocity_head_ft(velocity_ft_s: float) -> float:
    """Velocity head v^2/(2g) in feet."""
    return velocity_ft_s * velocity_ft_s / (2.0 * GRAVITY_FT_S2)


# --- Hazen-Williams friction loss ------------------------------------------


def hazen_williams_friction_loss_ft(
    flow_gpm: float,
    diameter_in: float,
    length_ft: float,
    c_factor: float,
) -> float:
    """Friction head loss per the CMA-form Hazen-Williams equation.

    Matches spreadsheet TDH!D21 exactly:
        hf = 0.002083 * L * (100/C)^1.85 * Q^1.85 / D^4.8655
    """
    if flow_gpm == 0.0:
        return 0.0
    if diameter_in <= 0.0:
        raise ValueError("Pipe diameter must be > 0.")
    if c_factor <= 0.0:
        raise ValueError("Hazen-Williams C must be > 0.")
    if length_ft < 0.0:
        raise ValueError("Pipe length must be >= 0.")
    return (
        HAZEN_WILLIAMS_COEFF_US
        * length_ft
        * (100.0 / c_factor) ** 1.85
        * flow_gpm ** 1.85
        / diameter_in ** 4.8655
    )


# --- Per-segment head-loss summary -----------------------------------------


@dataclass(frozen=True)
class SegmentHeadLossAtFlow:
    """Velocity, velocity head, friction loss, and fitting loss for one
    segment at one flow rate."""

    segment_label: str
    flow_gpm: float
    velocity_ft_s: float
    velocity_head_ft: float
    friction_loss_ft: float
    fitting_loss_ft: float

    @property
    def total_loss_ft(self) -> float:
        return self.friction_loss_ft + self.fitting_loss_ft


def segment_head_loss(
    segment: ForceMainSegment, flow_gpm: float
) -> SegmentHeadLossAtFlow:
    """Compute all head-loss components for one force-main segment at one flow."""
    v = pipe_velocity_ft_s(flow_gpm, segment.diameter_in)
    hv = velocity_head_ft(v)
    hf = hazen_williams_friction_loss_ft(
        flow_gpm, segment.diameter_in, segment.length_ft, segment.c_factor
    )
    h_fittings = hv * segment.total_k
    return SegmentHeadLossAtFlow(
        segment_label=segment.label,
        flow_gpm=flow_gpm,
        velocity_ft_s=v,
        velocity_head_ft=hv,
        friction_loss_ft=hf,
        fitting_loss_ft=h_fittings,
    )


# --- TDH curve --------------------------------------------------------------


@dataclass(frozen=True)
class TDHPoint:
    """One row of the TDH table: flow + per-segment losses + total TDH."""

    flow_gpm: float
    static_head_ft: float
    segment_losses: list[SegmentHeadLossAtFlow]

    @property
    def total_dynamic_head_ft(self) -> float:
        return self.static_head_ft + sum(
            s.total_loss_ft for s in self.segment_losses
        )


@dataclass(frozen=True)
class TDHCurve:
    """A TDH curve generated across a flow range."""

    static_head_ft: float
    segments: list[ForceMainSegment]
    points: list[TDHPoint]

    def flows_gpm(self) -> list[float]:
        return [p.flow_gpm for p in self.points]

    def tdh_ft(self) -> list[float]:
        return [p.total_dynamic_head_ft for p in self.points]


def build_tdh_curve(
    static_head_ft: float,
    segments: list[ForceMainSegment],
    flow_min_gpm: float = 0.0,
    flow_max_gpm: float = 2400.0,
    flow_increment_gpm: float = 60.0,
) -> TDHCurve:
    """Generate a TDH curve over a flow range.

    Defaults match the CMA spreadsheet 'TDH' tab (0-2400 GPM at 60 GPM
    increments, 41 rows).
    """
    if flow_increment_gpm <= 0.0:
        raise ValueError("Flow increment must be > 0.")
    if flow_max_gpm < flow_min_gpm:
        raise ValueError("flow_max_gpm must be >= flow_min_gpm.")

    points: list[TDHPoint] = []
    q = flow_min_gpm
    # Use a tolerance to include the upper bound exactly.
    while q <= flow_max_gpm + 1e-9:
        seg_losses = [segment_head_loss(s, q) for s in segments]
        points.append(
            TDHPoint(
                flow_gpm=q,
                static_head_ft=static_head_ft,
                segment_losses=seg_losses,
            )
        )
        q += flow_increment_gpm

    return TDHCurve(
        static_head_ft=static_head_ft, segments=list(segments), points=points
    )
