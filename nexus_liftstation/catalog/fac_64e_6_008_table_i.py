"""Curated subset of FAC 64E-6.008 Table I 'Estimated Sewage Inflows'.

Source: Florida Administrative Code 64E-6.008, Department of Health,
'System Size Determinations'. The PDF reference linked in CMA's design
package is at:
    https://www.columbiacountyfla.com/Downloads/Building%20&%20Zoning/
    Concurrency/64E-6.008,%20Florida%20Administrative%20Code.pdf

This module exposes a curated subset of the table covering the categories
CMA most commonly uses. The full table has dozens of rows for marinas,
churches, theaters, etc.; the senior designer can extend ``ENTRIES`` as
needed. Each entry is a (category, description, units_label, flow_gpd_per_unit).

VERIFICATION NOTE:
The PDF excerpt shown in the CMA reference uses 300 GPD for "Single Family
Homes (3 bedrooms w/ 1201-2250 sq ft)". The base FAC 64E-6.008 Table I
uses bedroom count rather than house size; the 300 GPD value is consistent
with the standard 3-bedroom row. A senior designer should verify against
the current FAC text before finalizing any specific design.

The values here are loaded as a Python dict so the senior designer can
swap them out with a YAML/JSON loader later without changing call sites.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import StructureCategory


@dataclass(frozen=True)
class TableIEntry:
    """One row of FAC 64E-6.008 Table I."""

    key: str
    category: StructureCategory
    description: str
    units_label: str
    flow_gpd_per_unit: float


#: Curated subset. Keys are short ASCII identifiers for the API to use.
#: The senior designer should extend this from the official current FAC text.
ENTRIES: dict[str, TableIEntry] = {
    # -- Residential --------------------------------------------------------
    "sfh_1br": TableIEntry(
        key="sfh_1br",
        category=StructureCategory.RESIDENTIAL,
        description="Single Family Home, 1 bedroom",
        units_label="dwelling unit",
        flow_gpd_per_unit=150.0,
    ),
    "sfh_2br": TableIEntry(
        key="sfh_2br",
        category=StructureCategory.RESIDENTIAL,
        description="Single Family Home, 2 bedrooms",
        units_label="dwelling unit",
        flow_gpd_per_unit=225.0,
    ),
    "sfh_3br": TableIEntry(
        key="sfh_3br",
        category=StructureCategory.RESIDENTIAL,
        description="Single Family Home, 3 bedrooms (1201-2250 sq ft)",
        units_label="dwelling unit",
        flow_gpd_per_unit=300.0,
    ),
    "sfh_4br": TableIEntry(
        key="sfh_4br",
        category=StructureCategory.RESIDENTIAL,
        description="Single Family Home, 4 bedrooms",
        units_label="dwelling unit",
        flow_gpd_per_unit=375.0,
    ),
    "apartment_1br": TableIEntry(
        key="apartment_1br",
        category=StructureCategory.RESIDENTIAL,
        description="Apartment, 1 bedroom",
        units_label="dwelling unit",
        flow_gpd_per_unit=150.0,
    ),
    "apartment_2br": TableIEntry(
        key="apartment_2br",
        category=StructureCategory.RESIDENTIAL,
        description="Apartment, 2 bedrooms",
        units_label="dwelling unit",
        flow_gpd_per_unit=225.0,
    ),
    "mobile_home_park": TableIEntry(
        key="mobile_home_park",
        category=StructureCategory.RESIDENTIAL,
        description="Mobile Home Park, per home",
        units_label="dwelling unit",
        flow_gpd_per_unit=200.0,
    ),
    # -- Institutional ------------------------------------------------------
    "school_no_meals_no_showers": TableIEntry(
        key="school_no_meals_no_showers",
        category=StructureCategory.INSTITUTIONAL,
        description="Day-type school, no meals or showers",
        units_label="student or staff",
        flow_gpd_per_unit=10.0,
    ),
    "school_with_cafeteria": TableIEntry(
        key="school_with_cafeteria",
        category=StructureCategory.INSTITUTIONAL,
        description="School with cafeteria, no showers",
        units_label="student or staff",
        flow_gpd_per_unit=15.0,
    ),
    "school_with_cafeteria_showers": TableIEntry(
        key="school_with_cafeteria_showers",
        category=StructureCategory.INSTITUTIONAL,
        description="School with cafeteria, gym and showers",
        units_label="student or staff",
        flow_gpd_per_unit=20.0,
    ),
    "hospital": TableIEntry(
        key="hospital",
        category=StructureCategory.INSTITUTIONAL,
        description="Hospital",
        units_label="bed",
        flow_gpd_per_unit=200.0,
    ),
    "nursing_home": TableIEntry(
        key="nursing_home",
        category=StructureCategory.INSTITUTIONAL,
        description="Nursing home",
        units_label="bed",
        flow_gpd_per_unit=100.0,
    ),
    # -- Commercial ---------------------------------------------------------
    "office_building": TableIEntry(
        key="office_building",
        category=StructureCategory.COMMERCIAL,
        description="Office building",
        units_label="employee",
        flow_gpd_per_unit=20.0,
    ),
    "retail_store": TableIEntry(
        key="retail_store",
        category=StructureCategory.COMMERCIAL,
        description="Retail store / shopping center",
        units_label="100 sq ft of floor area",
        flow_gpd_per_unit=10.0,
    ),
    "hotel_motel": TableIEntry(
        key="hotel_motel",
        category=StructureCategory.COMMERCIAL,
        description="Hotel / motel",
        units_label="bedroom",
        flow_gpd_per_unit=100.0,
    ),
    # -- Food service -------------------------------------------------------
    "restaurant_24hr": TableIEntry(
        key="restaurant_24hr",
        category=StructureCategory.FOOD_SERVICE,
        description="Restaurant, 24-hour operation",
        units_label="seat",
        flow_gpd_per_unit=70.0,
    ),
    "restaurant_single_service": TableIEntry(
        key="restaurant_single_service",
        category=StructureCategory.FOOD_SERVICE,
        description="Restaurant, single-service items only",
        units_label="seat",
        flow_gpd_per_unit=20.0,
    ),
    "restaurant_dining": TableIEntry(
        key="restaurant_dining",
        category=StructureCategory.FOOD_SERVICE,
        description="Restaurant, dining (not 24-hr)",
        units_label="seat",
        flow_gpd_per_unit=40.0,
    ),
    "bar_lounge": TableIEntry(
        key="bar_lounge",
        category=StructureCategory.FOOD_SERVICE,
        description="Bar / lounge",
        units_label="seat",
        flow_gpd_per_unit=20.0,
    ),
    # -- Industrial / Office ------------------------------------------------
    "factory_no_showers": TableIEntry(
        key="factory_no_showers",
        category=StructureCategory.INDUSTRIAL_OFFICE,
        description="Factory, no showers (sanitary only)",
        units_label="employee per shift",
        flow_gpd_per_unit=20.0,
    ),
    "factory_with_showers": TableIEntry(
        key="factory_with_showers",
        category=StructureCategory.INDUSTRIAL_OFFICE,
        description="Factory, with showers",
        units_label="employee per shift",
        flow_gpd_per_unit=35.0,
    ),
    "warehouse": TableIEntry(
        key="warehouse",
        category=StructureCategory.INDUSTRIAL_OFFICE,
        description="Warehouse, sanitary only",
        units_label="employee",
        flow_gpd_per_unit=20.0,
    ),
}


def get_entry(key: str) -> TableIEntry:
    """Look up a Table I entry by key. Raises KeyError if missing."""
    if key not in ENTRIES:
        raise KeyError(
            f"No FAC 64E-6.008 Table I entry for key '{key}'. "
            f"Available: {sorted(ENTRIES.keys())}"
        )
    return ENTRIES[key]


def list_entries() -> list[TableIEntry]:
    """List all curated Table I entries (for API enumeration)."""
    return list(ENTRIES.values())
