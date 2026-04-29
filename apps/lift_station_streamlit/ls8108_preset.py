"""LS8108 reference example, used as the default state for the Streamlit app.

These numbers reproduce the LS8108 design example from the CMA reference PDF
(Parameters_needed_for_Pump_Lift_Station_Design.pdf). Loading this preset
and hitting "Run Design" is the fastest way to confirm the calc engine
matches the PDF.
"""

from __future__ import annotations


def ls8108_inputs() -> dict:
    """Return a flat dict of all UI input values for the LS8108 reference."""
    return {
        # Project info
        "project_name": "LS8108 (Reference Example)",
        "project_number": "LS8108",
        "designer": "CMA",
        "project_location": "Florida",
        # Inflows: list of (catalog_key, num_units, residential_units_for_pop)
        # The school uses a custom override so it's expressed differently below.
        "inflow_rows": [
            {
                "catalog_key": "sfh_3br",
                "description_override": "",
                "flow_per_unit_gpd_override": 0.0,
                "number_of_units": 333,
                "residential_units_for_population": 333,
            },
            {
                "catalog_key": "__custom__",
                "description_override": "School (aggregate)",
                "flow_per_unit_gpd_override": 3758.0,
                "number_of_units": 1,
                "residential_units_for_population": 0,
            },
        ],
        # Wet well geometry
        "diameter_ft": 10.0,
        "flood_elevation_label": "ZONE X",
        "top_slab_el": 18.2,
        "finish_grade_el": 18.2,
        "centerline_discharge_pipe_el": 14.95,
        "lowest_influent_line_el": 4.486666666666667,
        "lead_pump_on_el": 3.4866666666666672,
        "both_pumps_off_el": -0.5133333333333328,
        "pump_suction_el": -2.18,
        "wetwell_base_slab_el": -2.5133333333333328,
        "pump_discharge_diameter_in": 4.0,
        "discharge_pipe_diameter_in": 6.0,
        "common_force_main_diameter_in": 10.0,
        "pump_dimension_in": 52.5,
        # Force main segments. Each is (label, dia, length, c_factor, fittings)
        # where fittings is a list of (name, k, qty).
        "force_main_segments": [
            {
                "label": "A",
                "diameter_in": 6.0,
                "length_ft": 58.0,
                "c_factor": 120.0,
                "fittings": [
                    {"name": "90 Degree Bend", "k": 0.45, "qty": 3},
                    {"name": "45 Degree Bend", "k": 0.24, "qty": 2},
                    {"name": "Swing Check Valve", "k": 1.5, "qty": 1},
                    {"name": "Gate Valve", "k": 0.12, "qty": 3},
                    {"name": "Standard Tee Thru-Flow", "k": 0.30, "qty": 2},
                    {"name": "Reducer", "k": 0.41, "qty": 1},
                ],
            },
            {
                "label": "B",
                "diameter_in": 10.0,
                "length_ft": 199.0,
                "c_factor": 120.0,
                "fittings": [
                    {"name": "45 Degree Bend", "k": 0.22, "qty": 2},
                    {"name": "Standard Tee Thru-Flow", "k": 0.28, "qty": 1},
                ],
            },
        ],
        # Static head
        "destination_elevation_ft": 14.95,
        "proposed_grade_elevation_ft": 18.20,
        "pump_off_elevation_ft": -0.5133333333333328,
        "static_head_at_connection_psi": 11.9,
        # Design pumping rate (rounded up from min)
        "design_pump_rate_gpm": 300.0,
        # Pump selection
        "selected_pump_key": "flygt_ns3085_small_PLACEHOLDER",
        # Buoyancy (only used if user opts in)
        "buoyancy_enabled": False,
        "rim_elevation_ft": 18.2,
        "second_pour_top_elevation_ft": -2.5133333333333328,
        "wall_thickness_in": 8.0,
        "top_slab_thickness_in": 6.0,
        "second_pour_wall_height_in": 16.0,
        "inside_diameter_ft": 10.0,
        "tremie_seal_height_below_second_pour_ft": 7.0,
        "water_density_lb_ft3": 62.43,
        "concrete_density_lb_ft3": 150.0,
        "safety_factor": 1.1,
        # System curve resolution
        "tdh_flow_max_gpm": 2400.0,
        "tdh_flow_increment_gpm": 60.0,
    }
