"""Regression test for LS8108 example.

Locks in the exact numbers from:
  - Parameters_needed_for_Pump_Lift_Station_Design.pdf (CMA reference)
  - Lift_Station_Calculations_Template.xlsx (CMA spreadsheet)

Any future change to the calc modules that breaks these numbers will fail
this test, and the maintainer must explicitly justify the new values.
"""

from __future__ import annotations

import math

import pytest

from nexus_liftstation.calc.cycle_time import (
    cycle_times,
    wet_well_working_volume,
)
from nexus_liftstation.calc.flow import estimate_flows
from nexus_liftstation.calc.head_loss import (
    build_tdh_curve,
    static_head,
)
from nexus_liftstation.calc.peak_factor import design_pumping_flow
from nexus_liftstation.models import (
    Fitting,
    ForceMainSegment,
    StaticHeadInputs,
    StructureCategory,
    StructureInflow,
)


# ---------------------------------------------------------------------------
# Reference inputs and expected values
# ---------------------------------------------------------------------------

LS8108_INFLOWS = [
    StructureInflow(
        category=StructureCategory.RESIDENTIAL,
        description="SFH 3BR",
        flow_per_unit_gpd=300.0,
        number_of_units=333,
        residential_units_for_population=333,
    ),
    StructureInflow(
        category=StructureCategory.INSTITUTIONAL,
        description="School",
        flow_per_unit_gpd=3758.0,
        number_of_units=1,
    ),
]


def test_flow_estimate_matches_pdf() -> None:
    """ADF and population from PDF page 7."""
    est = estimate_flows(LS8108_INFLOWS)
    # PDF: 103,658 GPD
    assert est.average_daily_flow_gpd == pytest.approx(103658.0, abs=0.01)
    # PDF rounds 832.5 to 833; we keep the unrounded value for precision.
    assert est.service_area_population == pytest.approx(832.5, abs=0.01)


def test_peak_factor_matches_pdf() -> None:
    """Design PF, peak flow, min pumping rate, design pumping rate."""
    result = design_pumping_flow(
        average_daily_flow_gpd=103658.0,
        population=832.5,
    )
    assert result.peak_factor_result.fair_geyer_pf == pytest.approx(3.85, abs=0.005)
    assert result.peak_factor_result.governing_method == "fair_geyer"
    # PDF: 399,075 GPD (more precisely, the spreadsheet value 399075.26)
    assert result.peak_flow_gpd == pytest.approx(399075.26, abs=0.5)
    # PDF: 277.14 GPM
    assert result.minimum_pumping_rate_gpm == pytest.approx(277.135, abs=0.01)
    # PDF: 300 GPM (round up from 277 to nearest 100)
    assert result.recommended_pumping_rate_gpm == 300.0


def test_static_head_matches_spreadsheet() -> None:
    """Static head matches CMA spreadsheet 'Headloss Fitting' D13 = 42.95."""
    sh = static_head(
        StaticHeadInputs(
            destination_elevation_ft=14.95,
            proposed_grade_elevation_ft=18.20,
            pump_off_elevation_ft=-0.5133333333333328,
            static_head_at_connection_psi=11.9,
        )
    )
    assert sh.static_lift_ft == pytest.approx(15.46333333, abs=1e-8)
    assert sh.static_head_at_connection_ft == pytest.approx(27.489, abs=1e-8)
    assert sh.total_static_head_ft == pytest.approx(42.95233333, abs=1e-8)


def test_wet_well_volume_matches_spreadsheet() -> None:
    """Working volume matches spreadsheet 'Pump Cycle Times' D32 = 2349.911."""
    v = wet_well_working_volume(
        diameter_ft=10.0,
        lead_pump_on_el_ft=3.4866666666666672,
        both_pumps_off_el_ft=-0.5133333333333328,
    )
    assert v.working_depth_ft == pytest.approx(4.0, abs=1e-12)
    assert v.volume_gal == pytest.approx(2349.911304885166, abs=1e-9)


def test_cycle_times_match_spreadsheet() -> None:
    """All five cycle times match spreadsheet (with documented divergence)."""
    ct = cycle_times(
        volume_gal=2349.9113048851655,
        q_avg_gpm=10.416666666666666,
        q_peak_gpm=36.546339798473255,
        q_pump_gpm=100.0,
    )
    # Spreadsheet stored values (Pump Cycle Times tab, D42-D50):
    assert ct.t_min_min == pytest.approx(93.99645219540662, abs=1e-9)
    # Tavg run uses (Qpeak-Qavg) per spreadsheet (DIVERGENCE):
    assert ct.t_avg_run_min == pytest.approx(89.93267129793192, abs=1e-9)
    assert ct.t_avg_cycle_min == pytest.approx(315.52415656690783, abs=1e-9)
    assert ct.t_peak_run_min == pytest.approx(37.03350283375182, abs=1e-9)
    assert ct.t_peak_cycle_min == pytest.approx(101.33300089137492, abs=1e-9)


def test_tdh_curve_matches_spreadsheet() -> None:
    """TDH at multiple flow points matches spreadsheet TDH tab to ~1e-13."""
    seg_a = ForceMainSegment(
        label="A", diameter_in=6.0, length_ft=58.0, c_factor=120.0,
        fittings=[Fitting("Aggregated", 4.70, 1)],
    )
    seg_b = ForceMainSegment(
        label="B", diameter_in=10.0, length_ft=199.0, c_factor=120.0,
        fittings=[Fitting("Aggregated", 0.72, 1)],
    )
    curve = build_tdh_curve(
        static_head_ft=42.95233333333333,
        segments=[seg_a, seg_b],
        flow_min_gpm=0.0,
        flow_max_gpm=2400.0,
        flow_increment_gpm=60.0,
    )
    expected = {
        0:    42.95233333333333,
        60:   43.02217511817618,
        120:  43.21774077678098,
        240:  43.96363837748713,
        480:  46.81613276648483,
        1200: 65.77216165440284,
        1800: 93.09945195917405,
        2400: 130.66892859794700,
    }
    by_flow = {p.flow_gpm: p.total_dynamic_head_ft for p in curve.points}
    for q, expected_tdh in expected.items():
        assert by_flow[q] == pytest.approx(expected_tdh, abs=1e-10), (
            f"Flow={q} GPM: got {by_flow[q]}, expected {expected_tdh}"
        )


def test_tdh_curve_velocity_matches_spreadsheet() -> None:
    """Velocity in segment A at 60 GPM matches TDH B21 = 0.6808."""
    seg_a = ForceMainSegment(
        label="A", diameter_in=6.0, length_ft=58.0, c_factor=120.0,
        fittings=[Fitting("Aggregated", 4.70, 1)],
    )
    curve = build_tdh_curve(
        static_head_ft=42.95233333333333,
        segments=[seg_a],
        flow_min_gpm=0.0,
        flow_max_gpm=120.0,
        flow_increment_gpm=60.0,
    )
    pt_60 = next(p for p in curve.points if p.flow_gpm == 60.0)
    assert pt_60.segment_losses[0].velocity_ft_s == pytest.approx(
        0.6808297348811447, abs=1e-12
    )
