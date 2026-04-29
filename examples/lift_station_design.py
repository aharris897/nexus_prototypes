"""End-to-end example: reproduce the LS8108 design from the CMA reference PDF.

This script builds a LiftStationProject matching the example in
Parameters_needed_for_Pump_Lift_Station_Design.pdf, runs the full design
procedure, and writes JSON, Excel, and PDF outputs to ./outputs/.

Numbers reproduced from the PDF example:
    Average Daily Flow:           103,658 GPD
    Service Area Population:      833 (333 SFH * 2.5)
    Fair-Geyer Peak Factor:       3.85
    Peak Flow:                    399,075 GPD
    Minimum Pumping Rate:         277.14 GPM
    Design Pumping Rate:          300 GPM (rounded up to 100)
    Total Static Head:            42.95 ft

Run:
    python examples/lift_station_design.py
"""

from __future__ import annotations

from pathlib import Path

from nexus_liftstation.calc.buoyancy import BuoyancyInputs
from nexus_liftstation.calc.design import run_full_design
from nexus_liftstation.catalog.pump_curves import load_bundled_catalog
from nexus_liftstation.models import (
    Fitting,
    ForceMainSegment,
    LiftStationProject,
    StaticHeadInputs,
    StructureCategory,
    StructureInflow,
    WetWellGeometry,
)
from nexus_liftstation.output.excel_renderer import render_excel
from nexus_liftstation.output.json_renderer import render_json
from nexus_liftstation.output.pdf_renderer import render_pdf


def build_ls8108_project() -> LiftStationProject:
    """Construct the LS8108 project as described in the PDF reference."""
    return LiftStationProject(
        project_name="LS8108 (Reference Example)",
        project_location="Florida",
        project_number="LS8108",
        designer="CMA",
        inflows=[
            StructureInflow(
                category=StructureCategory.RESIDENTIAL,
                description="Single-Family Homes (3BR, 1201-2250 sq ft)",
                flow_per_unit_gpd=300.0,
                number_of_units=333,
                residential_units_for_population=333,
            ),
            StructureInflow(
                category=StructureCategory.INSTITUTIONAL,
                description="School (aggregate)",
                flow_per_unit_gpd=3758.0,
                number_of_units=1,
            ),
        ],
        geometry=WetWellGeometry(
            station_number="LS8108",
            diameter_ft=10.0,
            flood_elevation="ZONE X",
            top_slab_el=18.2,
            finish_grade_el=18.2,
            centerline_discharge_pipe_el=14.95,
            lowest_influent_line_el=4.486666666666667,
            lead_pump_on_el=3.4866666666666672,
            both_pumps_off_el=-0.5133333333333328,
            pump_suction_el=-2.18,
            wetwell_base_slab_el=-2.5133333333333328,
            pump_discharge_diameter_in=4.0,
            discharge_pipe_diameter_in=6.0,
            common_force_main_diameter_in=10.0,
            pump_dimension_in=52.5,
        ),
        force_main=[
            ForceMainSegment(
                label="A",
                diameter_in=6.0,
                length_ft=58.0,
                c_factor=120.0,
                fittings=[
                    Fitting("90 Degree Bend", 0.45, 3),
                    Fitting("45 Degree Bend", 0.24, 2),
                    Fitting("Swing Check Valve", 1.5, 1),
                    Fitting("Gate Valve", 0.12, 3),
                    Fitting("Standard Tee Thru-Flow", 0.30, 2),
                    Fitting("Reducer", 0.41, 1),
                ],
            ),
            ForceMainSegment(
                label="B",
                diameter_in=10.0,
                length_ft=199.0,
                c_factor=120.0,
                fittings=[
                    Fitting("45 Degree Bend", 0.22, 2),
                    Fitting("Standard Tee Thru-Flow", 0.28, 1),
                ],
            ),
        ],
        static_head=StaticHeadInputs(
            destination_elevation_ft=14.95,
            proposed_grade_elevation_ft=18.20,
            pump_off_elevation_ft=-0.5133333333333328,
            static_head_at_connection_psi=11.9,
        ),
        design_pump_rate_gpm=300.0,
    )


def main() -> None:
    project = build_ls8108_project()

    # Pick a placeholder pump that's roughly sized for ~300 GPM @ ~50 ft TDH.
    catalog = load_bundled_catalog()
    pump = catalog["flygt_ns3085_small_PLACEHOLDER"]

    # Buoyancy inputs reasonable for a 10-ft wet well.
    buoyancy_inputs = BuoyancyInputs(
        rim_elevation_ft=18.2,
        second_pour_top_elevation_ft=-2.5133333333333328,
        wall_thickness_in=8.0,
        top_slab_thickness_in=6.0,
        second_pour_wall_height_in=16.0,
        inside_diameter_ft=10.0,
        tremie_seal_height_below_second_pour_ft=7.0,
        water_density_lb_ft3=62.43,
        concrete_density_lb_ft3=150.0,
        safety_factor=1.1,
    )

    report = run_full_design(
        project=project,
        selected_pump=pump,
        buoyancy_inputs=buoyancy_inputs,
        tdh_flow_max_gpm=2400.0,
        tdh_flow_increment_gpm=60.0,
    )

    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    json_path = render_json(report, out_dir / "LS8108_design.json")
    xlsx_path = render_excel(report, out_dir / "LS8108_design.xlsx")
    pdf_path = render_pdf(report, out_dir / "LS8108_design.pdf")

    print(f"Wrote JSON to: {json_path}")
    print(f"Wrote Excel to: {xlsx_path}")
    print(f"Wrote PDF to:   {pdf_path}")
    print()
    print("--- Key results ---")
    pf = report.pumping_flow
    if pf is not None:
        print(f"  Average Daily Flow:    {pf.average_daily_flow_gpd:>10,.0f} GPD")
        print(f"  Fair-Geyer PF:         {pf.peak_factor_result.fair_geyer_pf:>10.4f}")
        print(f"  Design PF:             {pf.peak_factor_result.design_pf:>10.4f}")
        print(f"  Peak Flow:             {pf.peak_flow_gpd:>10,.0f} GPD")
        print(f"  Min Pumping Rate:      {pf.minimum_pumping_rate_gpm:>10.2f} GPM")
        print(f"  Design Pumping Rate:   {pf.recommended_pumping_rate_gpm:>10.0f} GPM")
    if report.static_head is not None:
        print(f"  Total Static Head:     {report.static_head.total_static_head_ft:>10.2f} ft")
    if report.cycle_times is not None:
        ct = report.cycle_times
        print(f"  Tmin:                  {ct.t_min_min:>10.2f} min")
        print(f"  Tavg run:              {ct.t_avg_run_min:>10.2f} min")
        print(f"  Tavg cycle:            {ct.t_avg_cycle_min:>10.2f} min")
    if report.operating_point is not None:
        op = report.operating_point
        print(f"  Operating Pt (placeholder pump): "
              f"{op.flow_gpm:.1f} GPM @ {op.head_ft:.2f} ft")


if __name__ == "__main__":
    main()
