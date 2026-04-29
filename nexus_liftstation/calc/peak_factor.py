"""Peak-factor calculations.

Per the CMA Order of Operations (step 2), the design pumping flow rate is
based on the greater of two peaking-factor methods:

1. **Tiered table by Average Daily Flow** (CMA / utility-baseline practice):
       0           - 100,000 GPD : PF = 4.0
       100,000     - 250,000 GPD : PF = 3.5
       250,000     - 1,000,000   : PF = 3.0
       >= 1,000,000              : PF = 2.5

2. **Fair-Geyer formula** based on service-area population:
       PF = (18 + sqrt(P)) / (4 + sqrt(P))
   where P is population in thousands. CMA additionally floors this
   at 2.5.
   Source: Fair, G. M. and Geyer, J. C., "Water Supply and Waste-Water
   Disposal," 1st Ed., John Wiley & Sons, New York (1954), p. 136.

Per scoping decision: this module always returns BOTH methods so the
caller (and the design report) can show the sanity check, and the
greater of the two is used as the design value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..constants import PEAK_FACTOR_FLOOR


@dataclass(frozen=True)
class PeakFactorResult:
    """Both peak-factor methods, side-by-side, plus the design value."""

    #: Peak factor from the ADF tiered table (CMA practice).
    table_pf: float

    #: Peak factor from the Fair-Geyer population formula, with the 2.5 floor
    #: applied per CMA spreadsheet (Flow Rate!C21).
    fair_geyer_pf: float

    #: Greater of the two values; this is the design peak factor used to
    #: compute design peak flow.
    design_pf: float

    #: Which method drove the design value, for the report.
    governing_method: str  # "table" or "fair_geyer"


def table_peak_factor(average_daily_flow_gpd: float) -> float:
    """Return the CMA tiered-table peak factor for a given ADF (GPD).

    Matches spreadsheet Flow Rate!C14 logic.
    """
    if average_daily_flow_gpd < 100_000.0:
        return 4.0
    if average_daily_flow_gpd < 250_000.0:
        return 3.5
    if average_daily_flow_gpd < 1_000_000.0:
        return 3.0
    return 2.5


def fair_geyer_peak_factor(
    population: float, apply_floor: bool = True
) -> float:
    """Return the Fair-Geyer peak factor for a given service-area population.

    Args:
        population: Population in PEOPLE (NOT thousands). The formula
            internally converts to thousands.
        apply_floor: If True, returns max(formula, 2.5) per CMA practice.

    Returns:
        Peak factor (dimensionless).
    """
    if population <= 0.0:
        # Avoid math domain error; use the floor.
        return PEAK_FACTOR_FLOOR if apply_floor else float("nan")
    p_thousands = population / 1000.0
    pf = (18.0 + math.sqrt(p_thousands)) / (4.0 + math.sqrt(p_thousands))
    if apply_floor and pf < PEAK_FACTOR_FLOOR:
        return PEAK_FACTOR_FLOOR
    return pf


def design_peak_factor(
    average_daily_flow_gpd: float, population: float
) -> PeakFactorResult:
    """Compute both methods and return the greater as the design PF.

    Per scoping decision: ALWAYS computes both methods and reports both,
    even if one is obviously not governing.
    """
    table_pf = table_peak_factor(average_daily_flow_gpd)
    fg_pf = fair_geyer_peak_factor(population, apply_floor=True)

    if fg_pf >= table_pf:
        return PeakFactorResult(table_pf, fg_pf, fg_pf, "fair_geyer")
    return PeakFactorResult(table_pf, fg_pf, table_pf, "table")


@dataclass(frozen=True)
class DesignPumpingFlowResult:
    """Result of step 2: design peak flow + minimum required pumping rate.

    Mirrors the values displayed in spreadsheet Flow Rate!B23:D26.
    """

    average_daily_flow_gpd: float
    peak_factor_result: PeakFactorResult
    peak_flow_gpd: float
    minimum_pumping_rate_gpm: float
    #: Recommended pumping rate, rounded UP to nearest 100 GPM (matches
    #: spreadsheet ROUNDUP(C25,-2)).
    recommended_pumping_rate_gpm: float


def design_pumping_flow(
    average_daily_flow_gpd: float, population: float
) -> DesignPumpingFlowResult:
    """Compute the design peak flow and minimum pumping rate.

    Matches spreadsheet 'Flow Rate' tab logic:
        Peak Flow (GPD) = ADF * design_PF
        Min Pumping Rate (GPM) = Peak Flow / (24 * 60)
        Recommended Rate (GPM) = ROUNDUP(Min Rate, nearest 100)
    """
    pf = design_peak_factor(average_daily_flow_gpd, population)
    peak_gpd = average_daily_flow_gpd * pf.design_pf
    min_gpm = peak_gpd / (24.0 * 60.0)
    recommended_gpm = math.ceil(min_gpm / 100.0) * 100.0
    return DesignPumpingFlowResult(
        average_daily_flow_gpd=average_daily_flow_gpd,
        peak_factor_result=pf,
        peak_flow_gpd=peak_gpd,
        minimum_pumping_rate_gpm=min_gpm,
        recommended_pumping_rate_gpm=recommended_gpm,
    )
