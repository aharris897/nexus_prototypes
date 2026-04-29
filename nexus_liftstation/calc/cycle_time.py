"""Wet well volume and pump cycle time calculations.

Implements step 3 of the CMA Order of Operations.

The CMA spreadsheet ('Pump Cycle Times' tab) computes the working volume
between Lead Pump On (EL F) and Both Pumps Off (EL G):

  V (gal) = (pi * D^2 / 4) * (EL_F - EL_G) * 7.48

Cycle-time checks: this module reproduces the spreadsheet's exact formulas
(cells D42, D44, D46, D48, D50). Per scoping decision, backend matches
spreadsheet behavior verbatim. There is a noteworthy divergence between
those formulas and the textbook references; see DIVERGENCE NOTE below.

Spreadsheet formulas (matched exactly here):
  Tmin        = 4 * V / Qpump
  Tavg run    = V / (Qpeak - Qavg)               [<-- see DIVERGENCE]
  Tavg cycle  = V / (Qpeak - Qavg) + V / Qavg    [<-- see DIVERGENCE]
  Tpeak run   = V / (Qpump - Qpeak)
  Tpeak cycle = V / (Qpump - Qpeak) + V / Qpeak

DIVERGENCE NOTE (FOR SENIOR DESIGNER REVIEW):
The textbook formulas in the PDF reference (section 6.3.9.1) use Q_out =
pump rate in the denominator of the cycle-time expression:
    T_min = V/Q_in + V/(Q_out - Q_in)
The spreadsheet 'Tavg run' formula uses Qpeak - Qavg in the denominator
instead of Qpump - Qavg. This may be intentional (interpreting 'Tavg run'
as run time at average inflow during a peak-flow event in a multi-pump
station), or it may be a spreadsheet error. We match the spreadsheet
verbatim because the user directed us to. Senior designer should review
and decide whether to switch to the textbook form.

Spreadsheet specs for status checks (annotated next to each cell):
  Tmin > 5 min, Tavg run > 2 min, Tavg cycle < 30 min.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..constants import GAL_PER_FT3


@dataclass(frozen=True)
class WetWellVolumeResult:
    """Working volume between lead-pump-on and both-pumps-off."""

    diameter_ft: float
    lead_pump_on_el_ft: float
    both_pumps_off_el_ft: float
    working_depth_ft: float
    volume_gal: float


def wet_well_working_volume(
    diameter_ft: float,
    lead_pump_on_el_ft: float,
    both_pumps_off_el_ft: float,
) -> WetWellVolumeResult:
    """Compute the working volume of a circular wet well between set points.

    Matches spreadsheet 'Pump Cycle Times'!D32:
        V = pi * D^2 / 4 * (EL_F - EL_G) * 7.48

    Args:
        diameter_ft: Wet well inside diameter (ft).
        lead_pump_on_el_ft: 'EL F' elevation in chosen vertical datum.
        both_pumps_off_el_ft: 'EL G' elevation in same datum.

    Returns:
        WetWellVolumeResult with the computed volume in gallons.
    """
    if diameter_ft <= 0.0:
        raise ValueError(f"Wet well diameter must be > 0; got {diameter_ft}")
    depth_ft = lead_pump_on_el_ft - both_pumps_off_el_ft
    if depth_ft <= 0.0:
        raise ValueError(
            f"Lead-pump-on elevation ({lead_pump_on_el_ft}) must be above "
            f"both-pumps-off elevation ({both_pumps_off_el_ft})"
        )
    area_ft2 = math.pi * diameter_ft * diameter_ft / 4.0
    volume_gal = area_ft2 * depth_ft * GAL_PER_FT3
    return WetWellVolumeResult(
        diameter_ft=diameter_ft,
        lead_pump_on_el_ft=lead_pump_on_el_ft,
        both_pumps_off_el_ft=both_pumps_off_el_ft,
        working_depth_ft=depth_ft,
        volume_gal=volume_gal,
    )


@dataclass(frozen=True)
class CycleTimeResult:
    """All five cycle-time checks for a single-pump system."""

    volume_gal: float
    q_avg_gpm: float
    q_peak_gpm: float
    q_pump_gpm: float

    #: 4*V/Qpump (theoretical minimum, must be > 5 min per CMA template).
    t_min_min: float
    #: V/(Qpump - Qavg) at average inflow; spec >2 min.
    t_avg_run_min: float
    #: Tavg run + V/Qavg; spec <30 min.
    t_avg_cycle_min: float
    #: V/(Qpump - Qpeak) at peak inflow.
    t_peak_run_min: float
    #: Tpeak run + V/Qpeak.
    t_peak_cycle_min: float

    @property
    def passes_t_min(self) -> bool:
        return self.t_min_min > 5.0

    @property
    def passes_t_avg_run(self) -> bool:
        return self.t_avg_run_min > 2.0

    @property
    def passes_t_avg_cycle(self) -> bool:
        return self.t_avg_cycle_min < 30.0


def cycle_times(
    volume_gal: float,
    q_avg_gpm: float,
    q_peak_gpm: float,
    q_pump_gpm: float,
) -> CycleTimeResult:
    """Compute all five cycle-time checks (matches CMA spreadsheet exactly).

    Args:
        volume_gal: Working volume in gallons.
        q_avg_gpm: Average inflow (GPM) = ADF / (24 * 60).
        q_peak_gpm: Peak inflow (GPM) = peak flow / (24 * 60). Must be < q_pump.
        q_pump_gpm: Pump output rate at design point (GPM).

    Returns:
        CycleTimeResult with all five times.

    Raises:
        ValueError: If pump rate is not greater than peak inflow (would
            cause division by zero or negative cycle time).

    See module docstring DIVERGENCE NOTE re: 'Tavg run' / 'Tavg cycle'
    using Qpeak in denominator rather than Qpump.
    """
    if q_pump_gpm <= q_peak_gpm:
        raise ValueError(
            f"Pump rate ({q_pump_gpm} GPM) must exceed peak inflow "
            f"({q_peak_gpm} GPM); otherwise wet well overflows."
        )
    if q_peak_gpm <= q_avg_gpm:
        raise ValueError(
            f"Peak inflow ({q_peak_gpm} GPM) must exceed average inflow "
            f"({q_avg_gpm} GPM)."
        )
    if q_avg_gpm <= 0.0 or q_peak_gpm <= 0.0:
        raise ValueError("Average and peak inflows must be > 0.")

    t_min = 4.0 * volume_gal / q_pump_gpm
    # NOTE: The next two formulas use (q_peak - q_avg), matching the
    # spreadsheet exactly. See DIVERGENCE NOTE in module docstring.
    t_avg_run = volume_gal / (q_peak_gpm - q_avg_gpm)
    t_avg_cycle = t_avg_run + volume_gal / q_avg_gpm
    t_peak_run = volume_gal / (q_pump_gpm - q_peak_gpm)
    t_peak_cycle = t_peak_run + volume_gal / q_peak_gpm

    return CycleTimeResult(
        volume_gal=volume_gal,
        q_avg_gpm=q_avg_gpm,
        q_peak_gpm=q_peak_gpm,
        q_pump_gpm=q_pump_gpm,
        t_min_min=t_min,
        t_avg_run_min=t_avg_run,
        t_avg_cycle_min=t_avg_cycle,
        t_peak_run_min=t_peak_run,
        t_peak_cycle_min=t_peak_cycle,
    )


def minimum_submergence_simple_in(
    pump_inlet_diameter_in: float, flow_gpm: float
) -> float:
    """Minimum submergence to avoid vortexing (Hydraulic Institute simple form).

    Reference: Parameters PDF section 6.3.9.3, first form:
        S_min = D + 0.574 * Q / D^1.5

    Args:
        pump_inlet_diameter_in: Pump inlet bell diameter (inches).
        flow_gpm: Flow rate (GPM).

    Returns:
        Minimum submergence in inches.
    """
    if pump_inlet_diameter_in <= 0.0:
        raise ValueError("Pump inlet diameter must be > 0.")
    return (
        pump_inlet_diameter_in
        + 0.574 * flow_gpm / (pump_inlet_diameter_in ** 1.5)
    )
