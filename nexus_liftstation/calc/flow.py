"""Flow estimation: contributing inflows -> design average daily flow.

Implements step 1 of the CMA design procedure (Order of Operations,
Pump/Lift Station Design): tabulate sewage inflows from contributing
parcels using FAC 64E-6.008 Table I.

Reference: Florida Administrative Code 64E-6.008 (System Size Determinations).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import PERSONS_PER_RESIDENTIAL_UNIT
from ..models import StructureInflow


@dataclass(frozen=True)
class FlowEstimate:
    """Result of summing contributing inflows."""

    #: Sum of (units * GPD/unit) across all contributing structures (GPD).
    average_daily_flow_gpd: float

    #: Estimated service-area population. For dwelling-unit categories,
    #: 2.5 persons/unit per CMA standard. Other categories contribute 0
    #: unless their `residential_units_for_population` is set.
    service_area_population: float

    #: Per-row breakdown for the design report.
    line_items: list[StructureInflow]


def estimate_flows(
    inflows: list[StructureInflow],
    persons_per_unit: float = PERSONS_PER_RESIDENTIAL_UNIT,
) -> FlowEstimate:
    """Sum inflows and compute service-area population.

    Args:
        inflows: List of structures contributing to the lift station.
        persons_per_unit: Persons per residential dwelling unit. Default
            2.5 per CMA spreadsheet (Flow Rate!C18).

    Returns:
        A FlowEstimate with totals and the input line items preserved
        for the report.
    """
    if not inflows:
        return FlowEstimate(0.0, 0.0, [])

    adf_gpd = sum(item.average_daily_flow_gpd for item in inflows)

    pop = 0.0
    for item in inflows:
        if item.residential_units_for_population is not None:
            pop += item.residential_units_for_population * persons_per_unit

    return FlowEstimate(
        average_daily_flow_gpd=adf_gpd,
        service_area_population=pop,
        line_items=list(inflows),
    )
