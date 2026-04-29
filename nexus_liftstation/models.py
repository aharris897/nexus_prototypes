"""Data classes describing a lift station project.

These are the inputs and intermediate structures that flow between calc modules.
They use dataclasses for clarity; the FastAPI layer converts to/from Pydantic
BaseModel automatically. Engineering inputs use named units (e.g. _ft, _gpm,
_in) in field names to make units explicit at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# --- Flow estimation inputs -------------------------------------------------


class StructureCategory(str, Enum):
    """High-level FAC 64E-6.008 Table I category groupings.

    The full Table I has dozens of rows; the curated subset in
    catalog/fac_64e_6_008_table_i.py implements the specific entries CMA
    uses most often. This enum lets the API surface a friendly drop-down.
    """

    RESIDENTIAL = "residential"
    INSTITUTIONAL = "institutional"
    COMMERCIAL = "commercial"
    FOOD_SERVICE = "food_service"
    INDUSTRIAL_OFFICE = "industrial_office"


@dataclass(frozen=True)
class StructureInflow:
    """One contributing land use / structure type in the basin.

    Attributes:
        category: Functional category (used for table lookup).
        description: Human-readable description that matches a Table I row.
        flow_per_unit_gpd: Estimated daily flow per unit (gallons per day).
        number_of_units: Count of units (homes, students, seats, etc.).
        residential_units_for_population: If this row should count toward
            service-area population (e.g. dwelling units), set to the
            number of dwelling units. None if not applicable.
    """

    category: StructureCategory
    description: str
    flow_per_unit_gpd: float
    number_of_units: float
    residential_units_for_population: float | None = None

    @property
    def average_daily_flow_gpd(self) -> float:
        return self.flow_per_unit_gpd * self.number_of_units


# --- Wet well geometry / set points ----------------------------------------


@dataclass
class WetWellGeometry:
    """Wet well dimensions and set-point elevations.

    All elevations in feet (NAVD88 or chosen vertical datum).
    Field names match labels in spreadsheet 'Pump Cycle Times' tab.
    """

    station_number: str = "LS XXXX"
    diameter_ft: float = 10.0
    flood_elevation: str | float = "ZONE X"
    top_slab_el: float = 0.0
    finish_grade_el: float = 0.0
    centerline_discharge_pipe_el: float = 0.0
    lowest_influent_line_el: float = 0.0  # "EL E"
    lead_pump_on_el: float = 0.0          # "EL F" = E - 12 in (typical)
    both_pumps_off_el: float = 0.0        # "EL G" = E - 60 in (typical)
    pump_suction_el: float = 0.0          # "EL H" = I + 4 in min
    wetwell_base_slab_el: float = 0.0     # "EL I" = E - 84 in (typical)
    pump_discharge_diameter_in: float = 4.0
    discharge_pipe_diameter_in: float = 6.0
    common_force_main_diameter_in: float = 6.0
    pump_dimension_in: float = 28.0       # from manufacturer cut sheet


# --- Force-main fittings ----------------------------------------------------


@dataclass(frozen=True)
class Fitting:
    """A single fitting/valve in the force main.

    Attributes:
        name: Display name (e.g. '90 Degree Bend').
        k_value: Resistance coefficient K for hf = K*v^2/(2g).
        quantity: Number of this fitting in this force-main segment.
    """

    name: str
    k_value: float
    quantity: int = 1

    @property
    def total_k(self) -> float:
        return self.k_value * self.quantity


@dataclass
class ForceMainSegment:
    """One segment of force main with its own diameter and fittings.

    The spreadsheet supports up to three FM segments (A=station, B=force
    main, C=optional). We support an arbitrary list.
    """

    label: str = "A"
    diameter_in: float = 6.0
    length_ft: float = 0.0
    c_factor: float = 120.0
    fittings: list[Fitting] = field(default_factory=list)

    @property
    def total_k(self) -> float:
        return sum(f.total_k for f in self.fittings)


# --- Static head -----------------------------------------------------------


@dataclass
class StaticHeadInputs:
    """Static-head components for the system-curve calculation."""

    destination_elevation_ft: float = 0.0
    proposed_grade_elevation_ft: float = 0.0
    pump_off_elevation_ft: float = 0.0
    static_head_at_connection_psi: float = 0.0


# --- Roll-up project --------------------------------------------------------


@dataclass
class LiftStationProject:
    """Top-level container for a single lift-station design case."""

    project_name: str = ""
    project_location: str = ""
    project_number: str = ""
    designer: str = ""

    inflows: list[StructureInflow] = field(default_factory=list)
    geometry: WetWellGeometry = field(default_factory=WetWellGeometry)
    force_main: list[ForceMainSegment] = field(default_factory=list)
    static_head: StaticHeadInputs = field(default_factory=StaticHeadInputs)

    #: Selected pump design point (GPM). Used by cycle-time and TDH calcs.
    design_pump_rate_gpm: float | None = None

    #: Optional override of design average flow (GPD). If None, computed from
    #: inflows.
    design_average_flow_gpd_override: float | None = None
