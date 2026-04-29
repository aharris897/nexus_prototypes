"""Nexus Lift Station design module.

Backend logic that automates the CMA (Chen Moore & Associates) sanitary
sewer lift station design workflow for Florida projects.

Mirrors the calculations in the CMA Lift Station Calculations Template
spreadsheet and the Order of Operations described in
Parameters_needed_for_Pump_Lift_Station_Design.pdf.

Public API entry points:
    - calc.design.run_full_design: top-level orchestrator.
    - output.{json,excel,pdf}_renderer.render_*: produce deliverables.
    - catalog.fac_64e_6_008_table_i.ENTRIES: inflow rates lookup.
    - catalog.k_values.get_k_value: fitting K lookup.
    - catalog.pump_curves.load_bundled_catalog: placeholder pump curves.
"""

__version__ = "0.1.0"
