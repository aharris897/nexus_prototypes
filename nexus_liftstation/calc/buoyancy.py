"""Buoyancy / flotation check for the wet well structure.

REPLICATES the CMA spreadsheet 'Buoyancy (Tremie)' tab single-case
calculation, per scoping decision.

DIVERGENCE NOTE FROM CMA STANDARD DETAIL NOTES 22 & 23:
The CMA standard detail (referenced elsewhere in the project) requires
TWO separate buoyancy load cases:
    - 25-yr construction stage (no top slab)
    - 100-yr final stage (with secondary pour)
and explicitly excludes top slab, secondary pour, pumps, and skin friction
from resisting weight in certain checks.

This module implements ONLY what the spreadsheet does: a single load case
with a 1.1 safety factor on buoyancy and total resisting weight = walls +
tremie seal at concrete density. The 'omitting skin friction' note in the
spreadsheet is preserved as documentation. Senior designer should review
whether to add the second load case before production use.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..constants import INCHES_PER_FOOT


@dataclass
class BuoyancyInputs:
    """Inputs to the wet well buoyancy check.

    Field names and defaults match the spreadsheet 'Buoyancy (Tremie)' tab.
    """

    rim_elevation_ft: float
    second_pour_top_elevation_ft: float
    wall_thickness_in: float = 8.0
    top_slab_thickness_in: float = 6.0
    second_pour_wall_height_in: float = 16.0
    inside_diameter_ft: float = 6.0
    #: Tremie seal extends 7 ft below the second-pour top elevation
    #: (matches spreadsheet D9 = D8 - 7).
    tremie_seal_height_below_second_pour_ft: float = 7.0
    #: Spreadsheet uses 62.43 lb/ft^3 (slightly higher than 62.37 used
    #: elsewhere; matched verbatim).
    water_density_lb_ft3: float = 62.43
    concrete_density_lb_ft3: float = 150.0
    safety_factor: float = 1.1


@dataclass(frozen=True)
class BuoyancyResult:
    """Result of the single-case buoyancy check.

    Replicates the values shown in spreadsheet cells D19, D20, D23, D29,
    D30, D32, D35, H35.
    """

    outside_diameter_ft: float
    height_of_structure_ft: float
    tremie_seal_height_ft: float
    volume_displaced_cf: float
    buoyant_force_lb: float
    factored_buoyant_force_lb: float
    volume_of_walls_cf: float
    volume_of_tremie_seal_cf: float
    total_weight_lb: float
    weight_to_buoyancy_ratio: float
    passes_check: bool
    note: str = (
        "Single-case check, omits skin friction. See module DIVERGENCE NOTE."
    )


def buoyancy_check(inputs: BuoyancyInputs) -> BuoyancyResult:
    """Single-case buoyancy/flotation check matching the CMA spreadsheet.

    Cell-by-cell mapping to spreadsheet 'Buoyancy (Tremie)' tab:
        D7  = top_slab_thickness / 12
        D9  = second_pour_top_el - 7
        D11 = wall_thickness / 12
        D12 = inside_diameter + 2 * wall_thickness_ft     (Do)
        D15 = abs(D9 - D8)                                (tremie height w)
        D16 = (rim - top_slab_thick_ft) - D9              (height h)
        D19 = (pi/4) * Do^2 * h                           (Volume displaced)
        D20 = D19 * water_density                         (Fb)
        D23 = SF * D20
        D29 = (pi/4) * (Do^2 - Di^2) * h                  (wall volume)
        D30 = (pi/4) * Di^2 * w                           (tremie seal vol)
        D32 = (D29 + D30) * concrete_density              (total weight)
        H35 = D32 / D20                                   (ratio)
        Pass = D32 > D20 (and ratio >= SF for true safety)

    Note: The spreadsheet's D35 cell only checks D32 > D20 (raw, not
    factored). H35 separately shows the ratio. Spec column G35 = 1.1.
    We implement the strict version: pass if ratio >= safety_factor.
    """
    wall_thick_ft = inputs.wall_thickness_in / INCHES_PER_FOOT
    top_slab_thick_ft = inputs.top_slab_thickness_in / INCHES_PER_FOOT

    do = inputs.inside_diameter_ft + 2.0 * wall_thick_ft
    di = inputs.inside_diameter_ft

    bottom_of_struct_el = (
        inputs.second_pour_top_elevation_ft
        - inputs.tremie_seal_height_below_second_pour_ft
    )
    tremie_height_w = abs(
        bottom_of_struct_el - inputs.second_pour_top_elevation_ft
    )
    height_h = (
        (inputs.rim_elevation_ft - top_slab_thick_ft) - bottom_of_struct_el
    )

    area_outer = math.pi / 4.0 * do * do
    area_inner = math.pi / 4.0 * di * di
    volume_displaced = area_outer * height_h
    buoyant_force = volume_displaced * inputs.water_density_lb_ft3
    factored_buoyant = inputs.safety_factor * buoyant_force

    volume_walls = (area_outer - area_inner) * height_h
    volume_tremie = area_inner * tremie_height_w
    total_weight = (volume_walls + volume_tremie) * inputs.concrete_density_lb_ft3

    ratio = total_weight / buoyant_force if buoyant_force > 0.0 else float("inf")
    passes = ratio >= inputs.safety_factor

    return BuoyancyResult(
        outside_diameter_ft=do,
        height_of_structure_ft=height_h,
        tremie_seal_height_ft=tremie_height_w,
        volume_displaced_cf=volume_displaced,
        buoyant_force_lb=buoyant_force,
        factored_buoyant_force_lb=factored_buoyant,
        volume_of_walls_cf=volume_walls,
        volume_of_tremie_seal_cf=volume_tremie,
        total_weight_lb=total_weight,
        weight_to_buoyancy_ratio=ratio,
        passes_check=passes,
    )
