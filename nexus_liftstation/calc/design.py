"""Top-level design orchestrator.

Runs the full CMA Order of Operations against a LiftStationProject and
returns a single `DesignReport` containing every intermediate result,
ready to be passed to any of the output renderers (Excel, PDF, JSON).
"""

from __future__ import annotations

from dataclasses import dataclass

from .buoyancy import BuoyancyInputs, BuoyancyResult, buoyancy_check
from .cycle_time import (
    CycleTimeResult,
    WetWellVolumeResult,
    cycle_times,
    wet_well_working_volume,
)
from .flow import FlowEstimate, estimate_flows
from .head_loss import (
    StaticHeadResult,
    TDHCurve,
    build_tdh_curve,
    static_head,
)
from .peak_factor import DesignPumpingFlowResult, design_pumping_flow
from .pump_match import OperatingPoint, find_operating_point
from ..catalog.pump_curves import PumpCurve
from ..models import LiftStationProject


@dataclass
class DesignReport:
    """Complete design results for a LiftStationProject.

    Any field can be None if its prerequisite data wasn't supplied.
    """

    project: LiftStationProject

    flow_estimate: FlowEstimate | None = None
    pumping_flow: DesignPumpingFlowResult | None = None
    static_head: StaticHeadResult | None = None
    tdh_curve: TDHCurve | None = None
    wet_well_volume: WetWellVolumeResult | None = None
    cycle_times: CycleTimeResult | None = None
    operating_point: OperatingPoint | None = None
    selected_pump: PumpCurve | None = None
    buoyancy: BuoyancyResult | None = None

    #: Free-text notes accumulated during design (warnings, divergences).
    notes: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


def run_full_design(
    project: LiftStationProject,
    selected_pump: PumpCurve | None = None,
    buoyancy_inputs: BuoyancyInputs | None = None,
    tdh_flow_max_gpm: float = 2400.0,
    tdh_flow_increment_gpm: float = 60.0,
) -> DesignReport:
    """Run the full design procedure and assemble a report.

    Args:
        project: Project inputs (inflows, geometry, force main, static head).
        selected_pump: Optional. If provided, the operating point is
            computed against this pump's curve.
        buoyancy_inputs: Optional. If provided, the buoyancy check is
            performed.
        tdh_flow_max_gpm: Upper bound for the system curve.
        tdh_flow_increment_gpm: Resolution of the system curve.

    Returns:
        A DesignReport with every available intermediate result.
    """
    report = DesignReport(project=project)

    # --- Step 1: flow estimation ------------------------------------------
    if project.inflows:
        report.flow_estimate = estimate_flows(project.inflows)

    # --- Step 2: peak factor + design pumping rate ------------------------
    adf = (
        project.design_average_flow_gpd_override
        if project.design_average_flow_gpd_override is not None
        else (
            report.flow_estimate.average_daily_flow_gpd
            if report.flow_estimate is not None
            else None
        )
    )
    pop = (
        report.flow_estimate.service_area_population
        if report.flow_estimate is not None
        else 0.0
    )
    if adf is not None:
        report.pumping_flow = design_pumping_flow(adf, pop)

    # --- Step 3: static head + TDH curve ---------------------------------
    report.static_head = static_head(project.static_head)
    if project.force_main:
        report.tdh_curve = build_tdh_curve(
            static_head_ft=report.static_head.total_static_head_ft,
            segments=project.force_main,
            flow_min_gpm=0.0,
            flow_max_gpm=tdh_flow_max_gpm,
            flow_increment_gpm=tdh_flow_increment_gpm,
        )

    # --- Step 4: wet well volume + cycle times ----------------------------
    geom = project.geometry
    if geom.diameter_ft > 0.0 and geom.lead_pump_on_el != geom.both_pumps_off_el:
        report.wet_well_volume = wet_well_working_volume(
            diameter_ft=geom.diameter_ft,
            lead_pump_on_el_ft=geom.lead_pump_on_el,
            both_pumps_off_el_ft=geom.both_pumps_off_el,
        )
    if (
        report.wet_well_volume is not None
        and report.pumping_flow is not None
        and project.design_pump_rate_gpm is not None
    ):
        q_avg_gpm = report.pumping_flow.average_daily_flow_gpd / (24.0 * 60.0)
        q_peak_gpm = report.pumping_flow.minimum_pumping_rate_gpm
        try:
            report.cycle_times = cycle_times(
                volume_gal=report.wet_well_volume.volume_gal,
                q_avg_gpm=q_avg_gpm,
                q_peak_gpm=q_peak_gpm,
                q_pump_gpm=project.design_pump_rate_gpm,
            )
        except ValueError as e:
            report.notes.append(f"Cycle time calc skipped: {e}")

    # --- Step 5: pump operating point -------------------------------------
    if (
        selected_pump is not None
        and report.tdh_curve is not None
        and project.design_pump_rate_gpm is not None
    ):
        report.selected_pump = selected_pump
        report.operating_point = find_operating_point(
            selected_pump,
            report.tdh_curve,
            target_design_gpm=project.design_pump_rate_gpm,
        )
        if selected_pump.is_placeholder:
            report.notes.append(
                f"WARNING: Selected pump '{selected_pump.model}' is "
                f"PLACEHOLDER data, not real manufacturer curves. "
                f"Replace before production use."
            )

    # --- Step 6: buoyancy --------------------------------------------------
    if buoyancy_inputs is not None:
        report.buoyancy = buoyancy_check(buoyancy_inputs)
        report.notes.append(
            "Buoyancy uses single-case spreadsheet replication, "
            "diverging from CMA Notes 22 & 23 (two-load-case)."
        )

    return report
