# nexus_liftstation

Backend module that automates the CMA (Chen Moore & Associates) sanitary-sewer lift-station design workflow for Florida projects. Mirrors the calculations in the *Lift Station Calculations Template* spreadsheet and the Order of Operations described in *Parameters_needed_for_Pump_Lift_Station_Design.pdf*.

This is a first-cut backend module dropped into the sandbox for a senior designer to review and integrate. Several intentional divergences from CMA standard details are flagged in code comments; please read the warnings section below before any production use.

## What this does

Given inputs about a contributing basin (parcels, land uses), a wet well (geometry, set points), a force main (pipes, fittings), and pump-system context (static head at connection point), the module computes:

1. Average daily flow from FAC 64E-6.008 Table I curated entries
2. Design peak factor (both tiered-table and Fair-Geyer methods, take greater)
3. Wet-well working volume and five cycle-time checks
4. Static head and the full TDH curve (Hazen-Williams + fitting losses)
5. Pump operating point (where pump curve crosses system curve)
6. Buoyancy / flotation check

…and produces JSON, Excel, and PDF deliverables.

## Verification status

Every value the module produces for the LS8108 reference example matches either the CMA reference PDF or the stored values in the CMA spreadsheet template — most to floating-point precision (1e-10 or better). The regression test in `tests/lift_station/test_ls8108_regression.py` locks these numbers in. Run `pytest tests/lift_station/` to confirm. 39 tests, all passing.

## Dependencies

This module adds the following to the sandbox's `requirements.txt`:

- `numpy` — numerical math
- `scipy` — PCHIP interpolation for pump curves, brentq for operating-point solve
- `openpyxl` — Excel rendering
- `reportlab` — PDF rendering

Python 3.11+ required (uses `from __future__ import annotations` and `dataclasses` patterns assuming modern typing).

## Quick start

```python
from nexus_liftstation.calc.design import run_full_design
from nexus_liftstation.catalog.pump_curves import load_bundled_catalog
from nexus_liftstation.output.json_renderer import render_json
from nexus_liftstation.output.excel_renderer import render_excel
from nexus_liftstation.output.pdf_renderer import render_pdf
from nexus_liftstation.models import (
    Fitting, ForceMainSegment, LiftStationProject, StaticHeadInputs,
    StructureCategory, StructureInflow, WetWellGeometry,
)

project = LiftStationProject(
    project_name="My Station",
    inflows=[StructureInflow(
        category=StructureCategory.RESIDENTIAL,
        description="SFH 3BR",
        flow_per_unit_gpd=300.0,
        number_of_units=100,
        residential_units_for_population=100,
    )],
    geometry=WetWellGeometry(
        diameter_ft=8.0, lead_pump_on_el=2.0, both_pumps_off_el=-2.0,
    ),
    force_main=[ForceMainSegment(
        label="A", diameter_in=6.0, length_ft=200.0, c_factor=120.0,
        fittings=[Fitting("90 Degree Bend", 0.45, 2)],
    )],
    static_head=StaticHeadInputs(
        destination_elevation_ft=15.0, pump_off_elevation_ft=-2.0,
        static_head_at_connection_psi=10.0,
    ),
    design_pump_rate_gpm=200.0,
)

pump = load_bundled_catalog()["flygt_ns3085_small_PLACEHOLDER"]
report = run_full_design(project, selected_pump=pump)

render_json(report, "out.json")
render_excel(report, "out.xlsx")
render_pdf(report, "out.pdf")
```

A complete reproducible example (LS8108 from the reference PDF) is in `examples/lift_station_design.py`:

```bash
python examples/lift_station_design.py
```

## Module layout

```
nexus_liftstation/
├── constants.py          - physical constants, unit conversions
├── models.py             - LiftStationProject and friends (plain dataclasses,
│                           NOT SQLAlchemy ORM models — see "Integration notes")
├── calc/                 - calculation modules
│   ├── flow.py
│   ├── peak_factor.py
│   ├── cycle_time.py
│   ├── head_loss.py
│   ├── buoyancy.py
│   ├── pump_match.py
│   └── design.py         - top-level orchestrator
├── catalog/              - reference data
│   ├── fac_64e_6_008_table_i.py
│   ├── k_values.py
│   └── pump_curves.py
├── data/pump_curves/     - bundled placeholder curve CSVs
└── output/               - renderers (JSON, Excel, PDF)
```

## Integration notes

The dataclasses in `nexus_liftstation/models.py` are plain Python dataclasses, not SQLAlchemy ORM models. This is deliberate — whether a lift station design should be a persisted entity (and how it relates to `User`, `ContractReview`, etc. in `nexus_core.models`) is a product decision the senior designer should own. To wire this into the database, mirror the dataclass shape into a `LiftStationDesign` ORM model in `nexus_core/models.py` and adapt at the edges.

## ⚠️ Important warnings before production use

### Pump curves are PLACEHOLDERS

The three bundled pump curves in `nexus_liftstation/data/pump_curves/` are **plausibly-shaped placeholder data, NOT real Flygt manufacturer curves**. Filenames contain `_PLACEHOLDER` and the `PumpCurve.is_placeholder` flag is set to `True`. The orchestrator emits a warning whenever a placeholder curve is selected.

To use real curves: contact a Xylem / Flygt rep and request engineering cut sheets for the relevant 3000-series N-pumps (typical municipal sanitary lift stations: NS 3085, NS 3127, NS 3153, NS 3171, NS 3202, NS 3301). Convert to CSV with columns `flow_gpm, head_ft, efficiency_pct, npshr_ft` and drop into `data/pump_curves/`.

### Cycle time formulas use the spreadsheet's form, not the textbook's

The CMA spreadsheet's `Tavg run` formula uses `V/(Qpeak - Qavg)` instead of the textbook's `V/(Qpump - Qavg)` (see `Parameters_needed_for_Pump_Lift_Station_Design.pdf` section 6.3.9.1). This module replicates the spreadsheet form and flags it with a `DIVERGENCE NOTE` in `calc/cycle_time.py`. Senior designer: please review whether to swap to the textbook form.

### Buoyancy is single-case

The spreadsheet's `Buoyancy (Tremie)` tab does only one load case. CMA standard detail Notes 22 & 23 require two load cases (25-yr construction + 100-yr final with secondary pour) and exclude the top slab, secondary pour, pumps, and skin friction from resisting weight. This module replicates the spreadsheet's behavior. See `DIVERGENCE NOTE` in `calc/buoyancy.py`.

## See also

- Repo root `README.md` — sandbox setup, ORM patterns, etc.
- `docs/lift_station_design_decisions.md` — full list of design decisions and debug notes from building this module.
