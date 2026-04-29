"""Unit tests for individual calc and catalog modules."""

from __future__ import annotations

import pytest

from nexus_liftstation.calc.buoyancy import (
    BuoyancyInputs,
    buoyancy_check,
)
from nexus_liftstation.calc.cycle_time import (
    cycle_times,
    minimum_submergence_simple_in,
    wet_well_working_volume,
)
from nexus_liftstation.calc.head_loss import (
    hazen_williams_friction_loss_ft,
    pipe_area_ft2,
    pipe_velocity_ft_s,
    velocity_head_ft,
)
from nexus_liftstation.calc.peak_factor import (
    fair_geyer_peak_factor,
    table_peak_factor,
)
from nexus_liftstation.calc.pump_match import find_operating_point
from nexus_liftstation.calc.head_loss import build_tdh_curve
from nexus_liftstation.catalog import fac_64e_6_008_table_i, k_values
from nexus_liftstation.catalog.pump_curves import (
    PumpCurve,
    PumpCurvePoint,
    load_bundled_catalog,
)
from nexus_liftstation.models import (
    Fitting,
    ForceMainSegment,
)


# --- peak factor ------------------------------------------------------------


@pytest.mark.parametrize(
    "adf_gpd, expected_pf",
    [
        (0.0, 4.0),
        (50_000.0, 4.0),
        (99_999.99, 4.0),
        (100_000.0, 3.5),
        (200_000.0, 3.5),
        (250_000.0, 3.0),
        (500_000.0, 3.0),
        (1_000_000.0, 2.5),
        (5_000_000.0, 2.5),
    ],
)
def test_table_peak_factor_buckets(adf_gpd: float, expected_pf: float) -> None:
    assert table_peak_factor(adf_gpd) == expected_pf


def test_fair_geyer_floor() -> None:
    """Floor is 2.5 per CMA spreadsheet."""
    # Very high population -> formula returns ~ 1.0 -> floored to 2.5.
    assert fair_geyer_peak_factor(1e9) == 2.5


def test_fair_geyer_known_point() -> None:
    """LS8108 reference: P=833 -> PF ~= 3.85."""
    assert fair_geyer_peak_factor(833.0) == pytest.approx(3.85, abs=0.005)


def test_fair_geyer_zero_population() -> None:
    """Zero population should return the floor without math errors."""
    assert fair_geyer_peak_factor(0.0) == 2.5


# --- head loss --------------------------------------------------------------


def test_pipe_area() -> None:
    """6-inch pipe area = pi * (0.5)^2 / 4 ft^2 = 0.19634954..."""
    assert pipe_area_ft2(6.0) == pytest.approx(0.19634954084936207, abs=1e-12)


def test_pipe_velocity_zero_flow() -> None:
    assert pipe_velocity_ft_s(0.0, 6.0) == 0.0


def test_velocity_head_simple() -> None:
    """v=1 ft/s -> hv = 1/(2*32.2) ~ 0.01553 ft."""
    assert velocity_head_ft(1.0) == pytest.approx(1.0 / 64.4, abs=1e-9)


def test_hazen_williams_zero_flow() -> None:
    assert hazen_williams_friction_loss_ft(0.0, 6.0, 100.0, 120.0) == 0.0


def test_hazen_williams_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        hazen_williams_friction_loss_ft(100.0, 0.0, 100.0, 120.0)
    with pytest.raises(ValueError):
        hazen_williams_friction_loss_ft(100.0, 6.0, 100.0, 0.0)
    with pytest.raises(ValueError):
        hazen_williams_friction_loss_ft(100.0, 6.0, -1.0, 120.0)


# --- cycle time -------------------------------------------------------------


def test_wet_well_volume_invalid_diameter() -> None:
    with pytest.raises(ValueError):
        wet_well_working_volume(0.0, 1.0, 0.0)


def test_wet_well_volume_invalid_depth() -> None:
    with pytest.raises(ValueError):
        wet_well_working_volume(10.0, 0.0, 1.0)


def test_cycle_times_invalid_pump_rate() -> None:
    """Pump rate must exceed peak inflow."""
    with pytest.raises(ValueError):
        cycle_times(volume_gal=1000.0, q_avg_gpm=10.0, q_peak_gpm=50.0, q_pump_gpm=40.0)


def test_minimum_submergence() -> None:
    """S_min = D + 0.574 * Q / D^1.5 with D=12 in, Q=500 GPM."""
    # 12 + 0.574 * 500 / 12^1.5 = 12 + 287/41.569 ~ 18.9 in
    s = minimum_submergence_simple_in(12.0, 500.0)
    assert s == pytest.approx(12.0 + 0.574 * 500.0 / (12.0 ** 1.5), abs=1e-9)


# --- buoyancy ---------------------------------------------------------------


def test_buoyancy_basic_shape() -> None:
    """A wet well that's clearly heavy enough to resist flotation passes."""
    inputs = BuoyancyInputs(
        rim_elevation_ft=20.0,
        second_pour_top_elevation_ft=-5.0,
        wall_thickness_in=12.0,
        top_slab_thickness_in=8.0,
        inside_diameter_ft=8.0,
    )
    result = buoyancy_check(inputs)
    assert result.outside_diameter_ft == pytest.approx(8.0 + 2 * (12.0 / 12.0), abs=1e-12)
    assert result.weight_to_buoyancy_ratio > 1.0  # thick walls + tremie -> safe


# --- catalog: K values ------------------------------------------------------


def test_k_value_lookup_gate_valve_6in() -> None:
    """6-inch gate valve K = 0.12 per Crane TP-410 / spreadsheet."""
    assert k_values.get_k_value("Gate Valve", 6.0) == 0.12


def test_k_value_lookup_case_insensitive() -> None:
    assert k_values.get_k_value("gate valve", 6.0) == 0.12


def test_k_value_unknown_fitting() -> None:
    with pytest.raises(KeyError):
        k_values.get_k_value("Unobtanium Valve", 6.0)


def test_k_value_pipe_size_extrapolation() -> None:
    """Sizes beyond the table top out at the largest bucket."""
    # 30" pipe falls outside table; should clamp to 18-24" bucket.
    k_30 = k_values.get_k_value("Gate Valve", 30.0)
    k_24 = k_values.get_k_value("Gate Valve", 24.0)
    assert k_30 == k_24


# --- catalog: FAC 64E-6.008 -------------------------------------------------


def test_table_i_lookup() -> None:
    e = fac_64e_6_008_table_i.get_entry("sfh_3br")
    assert e.flow_gpd_per_unit == 300.0


def test_table_i_unknown() -> None:
    with pytest.raises(KeyError):
        fac_64e_6_008_table_i.get_entry("does_not_exist")


# --- catalog: pump curves ---------------------------------------------------


def test_bundled_pump_catalog_loads() -> None:
    catalog = load_bundled_catalog()
    assert len(catalog) >= 1
    for curve in catalog.values():
        assert curve.is_placeholder, "All bundled curves should be placeholders."
        assert curve.flow_max_gpm > curve.flow_min_gpm
        # Head should monotonically decrease
        heads = [p.head_ft for p in curve.points]
        assert heads == sorted(heads, reverse=True)


def test_pump_curve_pchip_interpolation() -> None:
    """PCHIP returns intermediate values between curve points."""
    curve = PumpCurve(
        manufacturer="test",
        model="test_pump",
        points=[
            PumpCurvePoint(0.0, 100.0),
            PumpCurvePoint(100.0, 80.0),
            PumpCurvePoint(200.0, 50.0),
        ],
    )
    h_at_50 = curve.head_at(50.0)
    # Should be between 80 and 100.
    assert 80.0 < h_at_50 < 100.0


# --- pump matching ----------------------------------------------------------


def test_find_operating_point_intersection() -> None:
    """A flat system curve at 50 ft should intersect a placeholder pump."""
    seg = ForceMainSegment(
        label="A", diameter_in=6.0, length_ft=10.0, c_factor=120.0,
        fittings=[],
    )
    curve = build_tdh_curve(
        static_head_ft=30.0, segments=[seg],
        flow_min_gpm=0.0, flow_max_gpm=600.0, flow_increment_gpm=20.0,
    )
    pump = load_bundled_catalog()["flygt_ns3085_small_PLACEHOLDER"]
    op = find_operating_point(pump, curve, target_design_gpm=300.0)
    assert op.in_curve_range
    assert 0.0 < op.flow_gpm < 600.0
    assert op.head_ft > 0.0


def test_find_operating_point_no_intersection() -> None:
    """A system curve well above a tiny pump: no intersection."""
    pump = PumpCurve(
        manufacturer="test", model="tiny",
        points=[PumpCurvePoint(0.0, 5.0), PumpCurvePoint(100.0, 1.0)],
    )
    seg = ForceMainSegment(
        label="A", diameter_in=6.0, length_ft=10.0, c_factor=120.0,
        fittings=[],
    )
    curve = build_tdh_curve(
        static_head_ft=200.0, segments=[seg],
        flow_min_gpm=0.0, flow_max_gpm=100.0, flow_increment_gpm=20.0,
    )
    op = find_operating_point(pump, curve)
    assert not op.in_curve_range
