"""Lift Station QA/QC Streamlit app — proof-of-concept testing UI.

Run from the repo root:
    streamlit run apps/lift_station_streamlit/app.py

Pre-loads the LS8108 reference example. Hit "Run Design" immediately to
verify the calc engine matches the PDF's known-good numbers.

This is a throwaway QA/QC tool, NOT a production widget. The real frontend
will be built into Nexus separately.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Make the repo root importable so `import nexus_liftstation` works regardless
# of where streamlit was launched from.
_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parents[1]
for _p in (_REPO_ROOT, _APP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import streamlit as st  # noqa: E402

from nexus_liftstation.calc.buoyancy import BuoyancyInputs  # noqa: E402
from nexus_liftstation.calc.design import run_full_design  # noqa: E402
from nexus_liftstation.catalog import fac_64e_6_008_table_i, k_values  # noqa: E402
from nexus_liftstation.catalog.pump_curves import load_bundled_catalog  # noqa: E402
from nexus_liftstation.models import (  # noqa: E402
    Fitting,
    ForceMainSegment,
    LiftStationProject,
    StaticHeadInputs,
    StructureCategory,
    StructureInflow,
    WetWellGeometry,
)
from nexus_liftstation.output.excel_renderer import render_excel  # noqa: E402
from nexus_liftstation.output.json_renderer import report_to_dict  # noqa: E402
from nexus_liftstation.output.pdf_renderer import render_pdf  # noqa: E402

from ls8108_preset import ls8108_inputs  # noqa: E402


# =============================================================================
# Page setup
# =============================================================================

st.set_page_config(
    page_title="Lift Station QA/QC",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Session state initialization
# =============================================================================

def _ensure_state() -> None:
    """Load LS8108 preset into session_state on first run."""
    if "initialized" not in st.session_state:
        for k, v in ls8108_inputs().items():
            st.session_state[k] = v
        st.session_state["initialized"] = True


def _reset_to_ls8108() -> None:
    """Reset all inputs to the LS8108 reference."""
    for k, v in ls8108_inputs().items():
        st.session_state[k] = v


_ensure_state()


# =============================================================================
# Sidebar — project info, reset, and disclaimer
# =============================================================================

with st.sidebar:
    st.title("Lift Station QA/QC")
    st.caption("Proof-of-concept testing UI — not for production use")

    st.divider()

    st.subheader("Project info")
    st.text_input("Project name", key="project_name")
    st.text_input("Project number", key="project_number")
    st.text_input("Designer", key="designer")
    st.text_input("Location", key="project_location")

    st.divider()

    if st.button("Reset to LS8108 reference", use_container_width=True):
        _reset_to_ls8108()
        st.rerun()

    st.divider()

    with st.expander("⚠️ Read before trusting any output", expanded=False):
        st.markdown(
            """
            **Three things this tool may compute incorrectly for production
            purposes — review each before trusting numbers:**

            1. **Pump curves are PLACEHOLDER data**, not real Flygt cut sheets.
               Operating-point values will be off by 5–15% until real curves
               replace them.
            2. **Cycle-time `Tavg run`** uses the spreadsheet's `V/(Qpeak-Qavg)`
               formula instead of the textbook's `V/(Qpump-Qavg)`. See
               `calc/cycle_time.py`.
            3. **Buoyancy is single-case**; CMA Notes 22 & 23 require two
               load cases (25-yr construction + 100-yr final). See
               `calc/buoyancy.py`.

            Both #2 and #3 are flagged in the calc engine source. Senior
            designer should review.
            """
        )


# =============================================================================
# Main content
# =============================================================================

st.title("Lift Station Design — QA/QC Tool")
st.caption(
    "Pre-loaded with the LS8108 reference example. Hit **Run Design** "
    "below to verify against the PDF, then swap inputs to test variants."
)


# -----------------------------------------------------------------------------
# Section 1: Inflows
# -----------------------------------------------------------------------------

with st.expander("**1. Inflows** — contributing structures and land uses",
                 expanded=True):
    st.caption(
        "Add a row per land-use category. Pick from FAC 64E-6.008 Table I "
        "or use **Custom** for entries outside the catalog."
    )

    catalog_options = ["__custom__"] + list(fac_64e_6_008_table_i.ENTRIES.keys())

    def _label_for(key: str) -> str:
        if key == "__custom__":
            return "Custom (manual entry)"
        e = fac_64e_6_008_table_i.ENTRIES[key]
        return f"{e.description} ({e.flow_gpd_per_unit:g} gpd/{e.units_label})"

    if "inflow_rows" not in st.session_state:
        st.session_state["inflow_rows"] = []

    rows_to_delete = []
    for i, row in enumerate(st.session_state["inflow_rows"]):
        cols = st.columns([3, 2, 1.5, 1.5, 0.8])
        with cols[0]:
            # Defensive: if the saved key isn't in the catalog anymore,
            # fall back to "__custom__" so we don't crash.
            saved_key = row.get("catalog_key", "__custom__")
            if saved_key not in catalog_options:
                saved_key = "__custom__"
                row["catalog_key"] = saved_key
            new_key = st.selectbox(
                "Land use",
                options=catalog_options,
                format_func=_label_for,
                key=f"inflow_{i}_key",
                index=catalog_options.index(saved_key),
            )
            row["catalog_key"] = new_key

        with cols[1]:
            if new_key == "__custom__":
                row["description_override"] = st.text_input(
                    "Description",
                    value=row.get("description_override", ""),
                    key=f"inflow_{i}_desc",
                )
            else:
                e = fac_64e_6_008_table_i.ENTRIES[new_key]
                st.text_input(
                    "Description",
                    value=e.description,
                    key=f"inflow_{i}_desc_ro",
                    disabled=True,
                )

        with cols[2]:
            if new_key == "__custom__":
                row["flow_per_unit_gpd_override"] = st.number_input(
                    "GPD per unit",
                    value=float(row.get("flow_per_unit_gpd_override", 0.0)),
                    key=f"inflow_{i}_gpd",
                    min_value=0.0,
                    step=10.0,
                )
            else:
                e = fac_64e_6_008_table_i.ENTRIES[new_key]
                st.number_input(
                    "GPD per unit",
                    value=float(e.flow_gpd_per_unit),
                    key=f"inflow_{i}_gpd_ro",
                    disabled=True,
                )

        with cols[3]:
            row["number_of_units"] = st.number_input(
                "Units",
                value=int(row["number_of_units"]),
                key=f"inflow_{i}_units",
                min_value=0,
                step=1,
            )

        with cols[4]:
            st.write("")
            st.write("")
            if st.button("✕", key=f"inflow_{i}_del", help="Remove this row"):
                rows_to_delete.append(i)

        # Population count for residential entries
        is_residential = (
            new_key != "__custom__"
            and fac_64e_6_008_table_i.ENTRIES[new_key].category
            == StructureCategory.RESIDENTIAL
        )
        if is_residential:
            row["residential_units_for_population"] = st.number_input(
                "Residential units (for population × 2.5)",
                value=int(row.get("residential_units_for_population", 0)),
                key=f"inflow_{i}_pop",
                min_value=0,
                step=1,
                help=(
                    "Service area population is residential units × 2.5. "
                    "Used for the Fair-Geyer peaking factor."
                ),
            )
        else:
            row["residential_units_for_population"] = 0

    for idx in sorted(rows_to_delete, reverse=True):
        del st.session_state["inflow_rows"][idx]
        st.rerun()

    if st.button("+ Add inflow row"):
        st.session_state["inflow_rows"].append(
            {
                "catalog_key": "sfh_3br",
                "description_override": "",
                "flow_per_unit_gpd_override": 0.0,
                "number_of_units": 1,
                "residential_units_for_population": 1,
            }
        )
        st.rerun()


# -----------------------------------------------------------------------------
# Section 2: Wet well geometry
# -----------------------------------------------------------------------------

with st.expander("**2. Wet well geometry** — diameter and elevation set points",
                 expanded=False):
    cols = st.columns(2)
    with cols[0]:
        st.number_input("Diameter (ft)", key="diameter_ft",
                        min_value=0.0, step=0.5)
        st.text_input("Flood zone label", key="flood_elevation_label",
                      help="e.g. 'ZONE X' or '100-yr at EL 12.0'")
        st.number_input("Top slab EL", key="top_slab_el", step=0.1)
        st.number_input("Finish grade EL", key="finish_grade_el", step=0.1)
        st.number_input("Centerline discharge pipe EL",
                        key="centerline_discharge_pipe_el", step=0.1)
        st.number_input("Lowest influent line EL",
                        key="lowest_influent_line_el", step=0.1)
    with cols[1]:
        st.number_input("Lead pump ON EL", key="lead_pump_on_el", step=0.1)
        st.number_input("Both pumps OFF EL", key="both_pumps_off_el", step=0.1)
        st.number_input("Pump suction EL", key="pump_suction_el", step=0.1)
        st.number_input("Wet well base slab EL",
                        key="wetwell_base_slab_el", step=0.1)
        st.number_input("Pump discharge diameter (in)",
                        key="pump_discharge_diameter_in",
                        min_value=0.0, step=0.5)
        st.number_input("Discharge pipe diameter (in)",
                        key="discharge_pipe_diameter_in",
                        min_value=0.0, step=0.5)
        st.number_input("Common force main diameter (in)",
                        key="common_force_main_diameter_in",
                        min_value=0.0, step=0.5)


# -----------------------------------------------------------------------------
# Section 3: Force main segments
# -----------------------------------------------------------------------------

with st.expander("**3. Force main segments** — pipes and fittings",
                 expanded=False):
    st.caption(
        "Each segment runs from one diameter change to the next. K-values can "
        "be looked up from the catalog by clicking 'Look up K' below a fitting."
    )

    if "force_main_segments" not in st.session_state:
        st.session_state["force_main_segments"] = []

    segments_to_delete = []
    for seg_i, seg in enumerate(st.session_state["force_main_segments"]):
        st.markdown(f"#### Segment {seg['label']}")
        cols = st.columns([1, 2, 2, 2, 1])
        with cols[0]:
            seg["label"] = st.text_input(
                "Label", value=seg["label"], key=f"seg_{seg_i}_label",
                max_chars=4,
            )
        with cols[1]:
            seg["diameter_in"] = st.number_input(
                "Diameter (in)", value=float(seg["diameter_in"]),
                key=f"seg_{seg_i}_dia", min_value=0.0, step=0.5,
            )
        with cols[2]:
            seg["length_ft"] = st.number_input(
                "Length (ft)", value=float(seg["length_ft"]),
                key=f"seg_{seg_i}_len", min_value=0.0, step=10.0,
            )
        with cols[3]:
            seg["c_factor"] = st.number_input(
                "C-factor", value=float(seg["c_factor"]),
                key=f"seg_{seg_i}_c", min_value=80.0, max_value=160.0, step=5.0,
                help="Hazen-Williams C. DIP=120, PVC=150, etc.",
            )
        with cols[4]:
            st.write("")
            st.write("")
            if st.button("✕ Segment", key=f"seg_{seg_i}_del"):
                segments_to_delete.append(seg_i)

        # Fittings sub-table
        st.markdown("**Fittings**")
        fitting_options = k_values.list_fittings()

        fittings_to_delete = []
        for fit_i, fit in enumerate(seg["fittings"]):
            f_cols = st.columns([3, 1.5, 1.5, 1.5, 1])
            with f_cols[0]:
                # Use selectbox if name is in catalog, else free-text
                if fit["name"] in fitting_options:
                    new_name = st.selectbox(
                        "Fitting type",
                        options=fitting_options,
                        index=fitting_options.index(fit["name"]),
                        key=f"seg_{seg_i}_fit_{fit_i}_name",
                    )
                else:
                    new_name = st.text_input(
                        "Fitting type (custom)",
                        value=fit["name"],
                        key=f"seg_{seg_i}_fit_{fit_i}_name_custom",
                    )
                fit["name"] = new_name
            with f_cols[1]:
                fit["k"] = st.number_input(
                    "K-value", value=float(fit["k"]),
                    key=f"seg_{seg_i}_fit_{fit_i}_k",
                    min_value=0.0, step=0.05, format="%.3f",
                )
            with f_cols[2]:
                fit["qty"] = st.number_input(
                    "Quantity", value=int(fit["qty"]),
                    key=f"seg_{seg_i}_fit_{fit_i}_qty",
                    min_value=0, step=1,
                )
            with f_cols[3]:
                if st.button(
                    "Look up K",
                    key=f"seg_{seg_i}_fit_{fit_i}_lookup",
                    help=f"Catalog K for {fit['name']} at {seg['diameter_in']}\"",
                ):
                    try:
                        k_lookup = k_values.get_k_value(
                            fit["name"], seg["diameter_in"]
                        )
                        st.session_state[f"seg_{seg_i}_fit_{fit_i}_k"] = k_lookup
                        st.rerun()
                    except (KeyError, ValueError) as e:
                        st.warning(f"No catalog match: {e}")
            with f_cols[4]:
                st.write("")
                st.write("")
                if st.button("✕", key=f"seg_{seg_i}_fit_{fit_i}_del"):
                    fittings_to_delete.append(fit_i)

        for idx in sorted(fittings_to_delete, reverse=True):
            del seg["fittings"][idx]
            st.rerun()

        if st.button("+ Add fitting", key=f"seg_{seg_i}_add_fit"):
            seg["fittings"].append({"name": "90 Degree Bend", "k": 0.45,
                                    "qty": 1})
            st.rerun()

        st.divider()

    for idx in sorted(segments_to_delete, reverse=True):
        del st.session_state["force_main_segments"][idx]
        st.rerun()

    if st.button("+ Add force main segment"):
        next_label = chr(ord("A") + len(st.session_state["force_main_segments"]))
        st.session_state["force_main_segments"].append({
            "label": next_label,
            "diameter_in": 6.0,
            "length_ft": 100.0,
            "c_factor": 120.0,
            "fittings": [],
        })
        st.rerun()


# -----------------------------------------------------------------------------
# Section 4: Static head and design pumping rate
# -----------------------------------------------------------------------------

with st.expander("**4. Static head & design pumping rate**", expanded=False):
    cols = st.columns(2)
    with cols[0]:
        st.number_input("Destination elevation (ft)",
                        key="destination_elevation_ft", step=0.1,
                        help="Centerline of discharge pipe.")
        st.number_input("Proposed grade elevation (ft)",
                        key="proposed_grade_elevation_ft", step=0.1)
        st.number_input("Pump-off elevation (ft)",
                        key="pump_off_elevation_ft", step=0.1)
    with cols[1]:
        st.number_input("Static head at FM connection (psi)",
                        key="static_head_at_connection_psi",
                        min_value=0.0, step=0.5,
                        help=(
                            "Pressure at the point where the discharge force "
                            "main connects with the transmission main. "
                            "Use 0 if it discharges into a manhole."
                        ))
        st.number_input("Design pumping rate (GPM)",
                        key="design_pump_rate_gpm",
                        min_value=0.0, step=10.0,
                        help=(
                            "The rate you want each pump to deliver, "
                            "typically rounded up from the calculated minimum."
                        ))


# -----------------------------------------------------------------------------
# Section 5: Pump selection
# -----------------------------------------------------------------------------

with st.expander("**5. Pump selection**", expanded=False):
    pump_catalog = load_bundled_catalog()
    pump_keys = list(pump_catalog.keys())
    selected_pump_key = st.selectbox(
        "Pump (from bundled catalog)",
        options=pump_keys,
        index=pump_keys.index(st.session_state.get(
            "selected_pump_key", pump_keys[0]
        )),
        key="selected_pump_key",
    )
    pump = pump_catalog[selected_pump_key]
    if pump.is_placeholder:
        st.warning(
            "⚠️ This pump curve is **PLACEHOLDER data**. The shape is "
            "plausible but the numbers are not from a real Flygt cut sheet. "
            "Operating-point results will be off by 5–15%. Replace before "
            "any production use — see `data/pump_curves/README.md`."
        )

    cols = st.columns(2)
    with cols[0]:
        st.metric("Manufacturer", pump.manufacturer)
        st.metric("Model", pump.model)
    with cols[1]:
        st.metric("Impeller code", pump.impeller_code or "(not specified)")
        st.metric("Curve points", len(pump.points))


# -----------------------------------------------------------------------------
# Section 6: Buoyancy (optional)
# -----------------------------------------------------------------------------

with st.expander("**6. Buoyancy check** (optional)", expanded=False):
    st.checkbox("Run buoyancy check", key="buoyancy_enabled")
    if st.session_state["buoyancy_enabled"]:
        st.caption(
            "⚠️ This is a single-case calc replicating the spreadsheet's "
            "Buoyancy tab. CMA Notes 22 & 23 require two load cases."
        )
        cols = st.columns(2)
        with cols[0]:
            st.number_input("Rim elevation (ft)",
                            key="rim_elevation_ft", step=0.1)
            st.number_input("Second pour top elevation (ft)",
                            key="second_pour_top_elevation_ft", step=0.1)
            st.number_input("Wall thickness (in)",
                            key="wall_thickness_in", min_value=0.0, step=0.5)
            st.number_input("Top slab thickness (in)",
                            key="top_slab_thickness_in", min_value=0.0, step=0.5)
            st.number_input("Second pour wall height (in)",
                            key="second_pour_wall_height_in",
                            min_value=0.0, step=0.5)
        with cols[1]:
            st.number_input("Inside diameter (ft)",
                            key="inside_diameter_ft", min_value=0.0, step=0.5)
            st.number_input("Tremie seal height below 2nd pour (ft)",
                            key="tremie_seal_height_below_second_pour_ft",
                            min_value=0.0, step=0.5)
            st.number_input("Water density (lb/ft³)",
                            key="water_density_lb_ft3",
                            min_value=0.0, step=0.1)
            st.number_input("Concrete density (lb/ft³)",
                            key="concrete_density_lb_ft3",
                            min_value=0.0, step=1.0)
            st.number_input("Safety factor",
                            key="safety_factor",
                            min_value=1.0, step=0.05)


# -----------------------------------------------------------------------------
# Section 7: Advanced — system curve resolution
# -----------------------------------------------------------------------------

with st.expander("**7. Advanced** — system curve range", expanded=False):
    cols = st.columns(2)
    with cols[0]:
        st.number_input("Max flow on system curve (GPM)",
                        key="tdh_flow_max_gpm", min_value=100.0, step=100.0)
    with cols[1]:
        st.number_input("Flow increment (GPM)",
                        key="tdh_flow_increment_gpm",
                        min_value=10.0, step=10.0)


# =============================================================================
# Build LiftStationProject from current session state
# =============================================================================

def build_project_from_state() -> LiftStationProject:
    """Materialize a LiftStationProject from current session_state values."""
    inflows = []
    for row in st.session_state["inflow_rows"]:
        if row["catalog_key"] == "__custom__":
            # No "OTHER" category in the enum; default custom rows to
            # COMMERCIAL since most non-residential entries fall there.
            # Senior designer can extend StructureCategory if needed.
            category = StructureCategory.COMMERCIAL
            description = row["description_override"] or "(unnamed)"
            flow_per_unit = float(row["flow_per_unit_gpd_override"])
        else:
            entry = fac_64e_6_008_table_i.ENTRIES[row["catalog_key"]]
            category = entry.category
            description = entry.description
            flow_per_unit = float(entry.flow_gpd_per_unit)

        pop = row.get("residential_units_for_population", 0)
        inflows.append(StructureInflow(
            category=category,
            description=description,
            flow_per_unit_gpd=flow_per_unit,
            number_of_units=float(row["number_of_units"]),
            residential_units_for_population=(
                float(pop) if pop and pop > 0 else None
            ),
        ))

    geometry = WetWellGeometry(
        station_number=st.session_state["project_number"],
        diameter_ft=st.session_state["diameter_ft"],
        flood_elevation=st.session_state["flood_elevation_label"],
        top_slab_el=st.session_state["top_slab_el"],
        finish_grade_el=st.session_state["finish_grade_el"],
        centerline_discharge_pipe_el=st.session_state["centerline_discharge_pipe_el"],
        lowest_influent_line_el=st.session_state["lowest_influent_line_el"],
        lead_pump_on_el=st.session_state["lead_pump_on_el"],
        both_pumps_off_el=st.session_state["both_pumps_off_el"],
        pump_suction_el=st.session_state["pump_suction_el"],
        wetwell_base_slab_el=st.session_state["wetwell_base_slab_el"],
        pump_discharge_diameter_in=st.session_state["pump_discharge_diameter_in"],
        discharge_pipe_diameter_in=st.session_state["discharge_pipe_diameter_in"],
        common_force_main_diameter_in=st.session_state["common_force_main_diameter_in"],
        pump_dimension_in=st.session_state.get("pump_dimension_in", 28.0),
    )

    force_main = []
    for seg in st.session_state["force_main_segments"]:
        fittings = [
            Fitting(f["name"], float(f["k"]), int(f["qty"]))
            for f in seg["fittings"]
        ]
        force_main.append(ForceMainSegment(
            label=seg["label"],
            diameter_in=float(seg["diameter_in"]),
            length_ft=float(seg["length_ft"]),
            c_factor=float(seg["c_factor"]),
            fittings=fittings,
        ))

    static_head = StaticHeadInputs(
        destination_elevation_ft=st.session_state["destination_elevation_ft"],
        proposed_grade_elevation_ft=st.session_state["proposed_grade_elevation_ft"],
        pump_off_elevation_ft=st.session_state["pump_off_elevation_ft"],
        static_head_at_connection_psi=st.session_state["static_head_at_connection_psi"],
    )

    return LiftStationProject(
        project_name=st.session_state["project_name"],
        project_location=st.session_state["project_location"],
        project_number=st.session_state["project_number"],
        designer=st.session_state["designer"],
        inflows=inflows,
        geometry=geometry,
        force_main=force_main,
        static_head=static_head,
        design_pump_rate_gpm=float(st.session_state["design_pump_rate_gpm"]),
    )


def build_buoyancy_inputs() -> BuoyancyInputs | None:
    if not st.session_state["buoyancy_enabled"]:
        return None
    return BuoyancyInputs(
        rim_elevation_ft=st.session_state["rim_elevation_ft"],
        second_pour_top_elevation_ft=st.session_state["second_pour_top_elevation_ft"],
        wall_thickness_in=st.session_state["wall_thickness_in"],
        top_slab_thickness_in=st.session_state["top_slab_thickness_in"],
        second_pour_wall_height_in=st.session_state["second_pour_wall_height_in"],
        inside_diameter_ft=st.session_state["inside_diameter_ft"],
        tremie_seal_height_below_second_pour_ft=st.session_state[
            "tremie_seal_height_below_second_pour_ft"
        ],
        water_density_lb_ft3=st.session_state["water_density_lb_ft3"],
        concrete_density_lb_ft3=st.session_state["concrete_density_lb_ft3"],
        safety_factor=st.session_state["safety_factor"],
    )


# =============================================================================
# Run button
# =============================================================================

st.divider()

run_col, _, _ = st.columns([1, 2, 2])
with run_col:
    run_clicked = st.button("▶ Run Design", type="primary",
                            use_container_width=True)


# =============================================================================
# Results
# =============================================================================

if run_clicked:
    try:
        project = build_project_from_state()
        buoyancy_inputs = build_buoyancy_inputs()
        pump = load_bundled_catalog()[st.session_state["selected_pump_key"]]
        report = run_full_design(
            project=project,
            selected_pump=pump,
            buoyancy_inputs=buoyancy_inputs,
            tdh_flow_max_gpm=float(st.session_state["tdh_flow_max_gpm"]),
            tdh_flow_increment_gpm=float(
                st.session_state["tdh_flow_increment_gpm"]
            ),
        )
        st.session_state["last_report"] = report
    except Exception as exc:  # noqa: BLE001
        st.error(f"Design run failed: {exc}")
        st.exception(exc)
        st.stop()


report = st.session_state.get("last_report")

if report is None:
    st.info("Click **Run Design** above to compute results.")
else:
    st.header("Results")

    # ---- Notes / warnings ------------------------------------------------
    if report.notes:
        for note in report.notes:
            if "WARNING" in note or "PLACEHOLDER" in note:
                st.warning(note)
            else:
                st.info(note)

    # ---- Headline numbers ------------------------------------------------
    st.subheader("Headline numbers")
    pf = report.pumping_flow
    sh = report.static_head
    op = report.operating_point

    h_cols = st.columns(4)
    with h_cols[0]:
        st.metric(
            "Avg Daily Flow",
            f"{pf.average_daily_flow_gpd:,.0f} GPD" if pf else "—",
        )
    with h_cols[1]:
        st.metric(
            "Peak Flow",
            f"{pf.peak_flow_gpd:,.0f} GPD" if pf else "—",
        )
    with h_cols[2]:
        st.metric(
            "Min Pump Rate",
            f"{pf.minimum_pumping_rate_gpm:,.2f} GPM" if pf else "—",
        )
    with h_cols[3]:
        st.metric(
            "Total Static Head",
            f"{sh.total_static_head_ft:,.2f} ft" if sh else "—",
        )

    if op is not None:
        st.metric(
            "Operating Point (pump curve ∩ system curve)",
            f"{op.flow_gpm:,.1f} GPM @ {op.head_ft:,.2f} ft",
            help="Where the selected pump's curve crosses the system curve.",
        )
        if not op.in_curve_range:
            st.warning(
                "⚠️ Operating point is **outside the pump's published "
                "curve range** — the pump cannot deliver this duty point. "
                "Either resize the system or pick a different pump."
            )

    # ---- Step 1 detail: flow estimate -----------------------------------
    if report.flow_estimate is not None:
        with st.expander("**Step 1 detail** — Flow estimate", expanded=False):
            fe = report.flow_estimate
            st.write(f"**Average daily flow:** {fe.average_daily_flow_gpd:,.2f} GPD")
            st.write(f"**Service area population:** {fe.service_area_population:,.1f}")
            if fe.line_items:
                st.write("**Line items:**")
                rows = [
                    {
                        "Description": li.description,
                        "Category": li.category.value,
                        "Units": li.number_of_units,
                        "GPD/Unit": f"{li.flow_per_unit_gpd:,.1f}",
                        "Subtotal (GPD)": f"{li.average_daily_flow_gpd:,.1f}",
                    }
                    for li in fe.line_items
                ]
                st.dataframe(rows, hide_index=True, use_container_width=True)

    # ---- Step 2 detail: peak factor -------------------------------------
    if pf is not None:
        with st.expander("**Step 2 detail** — Peak factor & pumping rate",
                         expanded=False):
            pfr = pf.peak_factor_result
            cols = st.columns(2)
            with cols[0]:
                st.write(f"**Tiered-table PF:** {pfr.table_pf:.4f}")
                st.write(f"**Fair-Geyer PF:** {pfr.fair_geyer_pf:.4f}")
                st.write(f"**Design PF (greater):** {pfr.design_pf:.4f}")
                st.caption(f"Governing method: {pfr.governing_method}")
            with cols[1]:
                st.write(f"**Peak flow:** {pf.peak_flow_gpd:,.2f} GPD")
                st.write(f"**Min pumping rate:** "
                         f"{pf.minimum_pumping_rate_gpm:,.4f} GPM")
                st.write(f"**Recommended pumping rate:** "
                         f"{pf.recommended_pumping_rate_gpm:,.0f} GPM "
                         "(rounded up to next 100)")

    # ---- Step 3 detail: static head + TDH curve --------------------------
    if sh is not None:
        with st.expander("**Step 3 detail** — Static head & TDH",
                         expanded=False):
            cols = st.columns(2)
            with cols[0]:
                st.write(f"**Static lift:** {sh.static_lift_ft:,.4f} ft")
                st.write(f"**Static head at FM connection:** "
                         f"{sh.static_head_at_connection_ft:,.4f} ft "
                         f"({sh.static_head_at_connection_ft / 2.31:.2f} psi)")
                st.write(f"**Total static head:** "
                         f"{sh.total_static_head_ft:,.4f} ft")

    # ---- Step 4 detail: cycle times w/ pass/fail -------------------------
    if report.cycle_times is not None:
        with st.expander("**Step 4 detail** — Cycle times "
                         "(pass/fail vs spreadsheet thresholds)",
                         expanded=True):
            ct = report.cycle_times
            wv = report.wet_well_volume

            if wv is not None:
                st.write(f"**Wet-well working volume:** "
                         f"{wv.volume_gal:,.2f} gal "
                         f"(diameter {wv.diameter_ft:.1f} ft, "
                         f"depth {wv.working_depth_ft:.3f} ft)")

            def _check(label: str, value: float, threshold: float,
                       op: str, units: str = "min") -> dict:
                if op == ">":
                    ok = value > threshold
                    threshold_text = f"> {threshold} {units}"
                elif op == "<":
                    ok = value < threshold
                    threshold_text = f"< {threshold} {units}"
                else:
                    ok = True
                    threshold_text = "—"
                return {
                    "Quantity": label,
                    "Value": f"{value:,.3f} {units}",
                    "Threshold": threshold_text,
                    "Status": "✅ PASS" if ok else "❌ FAIL",
                }

            check_rows = [
                _check("T_min (filling time)", ct.t_min_min, 5.0, ">"),
                _check("T_avg run", ct.t_avg_run_min, 2.0, ">"),
                _check("T_avg cycle", ct.t_avg_cycle_min, 30.0, "<"),
                {
                    "Quantity": "T_peak run",
                    "Value": f"{ct.t_peak_run_min:,.3f} min",
                    "Threshold": "—",
                    "Status": "—",
                },
                {
                    "Quantity": "T_peak cycle",
                    "Value": f"{ct.t_peak_cycle_min:,.3f} min",
                    "Threshold": "—",
                    "Status": "—",
                },
            ]
            st.dataframe(check_rows, hide_index=True,
                         use_container_width=True)

            st.caption(
                "⚠️ **Divergence:** `Tavg run` here uses the spreadsheet's "
                "`V/(Qpeak−Qavg)` formula, NOT the textbook's "
                "`V/(Qpump−Qavg)`. See `calc/cycle_time.py` for details."
            )

    # ---- Step 5 detail: system curve + pump curve plot ------------------
    if report.tdh_curve is not None:
        with st.expander("**Step 5 detail** — System curve & pump curve",
                         expanded=True):
            tdh = report.tdh_curve
            tdh_flows = tdh.flows_gpm()
            tdh_heads = tdh.tdh_ft()

            try:
                import plotly.graph_objects as go

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=tdh_flows,
                    y=tdh_heads,
                    mode="lines+markers",
                    name="System curve (TDH)",
                    line=dict(color="#1f77b4", width=2),
                ))
                if report.selected_pump is not None:
                    pump_curve = report.selected_pump
                    pump_min = pump_curve.flow_min_gpm
                    pump_max = pump_curve.flow_max_gpm
                    flows_for_pump = [
                        f for f in tdh_flows if pump_min <= f <= pump_max
                    ]
                    pump_heads = [pump_curve.head_at(f) for f in flows_for_pump]
                    fig.add_trace(go.Scatter(
                        x=flows_for_pump,
                        y=pump_heads,
                        mode="lines+markers",
                        name=f"Pump curve ({pump_curve.model})",
                        line=dict(color="#d62728", width=2),
                    ))
                if op is not None:
                    fig.add_trace(go.Scatter(
                        x=[op.flow_gpm],
                        y=[op.head_ft],
                        mode="markers",
                        name="Operating point",
                        marker=dict(color="green", size=14,
                                    symbol="star"),
                    ))
                fig.update_layout(
                    xaxis_title="Flow (GPM)",
                    yaxis_title="Total Dynamic Head (ft)",
                    legend=dict(orientation="h",
                                yanchor="bottom", y=1.02,
                                xanchor="right", x=1),
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning(
                    "Install `plotly` for the chart: `pip install plotly`"
                )
                # Fall back to a table
                rows = [
                    {"Flow (GPM)": f, "TDH (ft)": h}
                    for f, h in zip(tdh_flows, tdh_heads)
                ]
                st.dataframe(rows, hide_index=True, use_container_width=True)

    # ---- Step 6 detail: buoyancy ----------------------------------------
    if report.buoyancy is not None:
        with st.expander("**Step 6 detail** — Buoyancy", expanded=False):
            b = report.buoyancy
            st.write(f"**Buoyant force:** {b.buoyant_force_lb:,.0f} lb")
            st.write(f"**Factored buoyant force (× SF):** "
                     f"{b.factored_buoyant_force_lb:,.0f} lb")
            st.write(f"**Total resisting weight:** {b.total_weight_lb:,.0f} lb")
            st.write(f"**Weight-to-buoyancy ratio:** "
                     f"{b.weight_to_buoyancy_ratio:.3f}")
            if b.passes_check:
                st.success("✅ Buoyancy check passes")
            else:
                st.error("❌ Buoyancy check FAILS — anti-flotation needed")
            st.caption(
                "⚠️ **Divergence:** Single-case calc replicating the "
                "spreadsheet. CMA Notes 22 & 23 require two load cases."
            )

    # ---- Downloads ------------------------------------------------------
    st.divider()
    st.subheader("Download deliverables")

    proj_name = report.project.project_name.replace(" ", "_").replace("/", "_")

    dl_cols = st.columns(3)
    with dl_cols[0]:
        json_str = json.dumps(report_to_dict(report), indent=2, default=str)
        st.download_button(
            label="⬇ Download JSON",
            data=json_str,
            file_name=f"{proj_name}_design.json",
            mime="application/json",
            use_container_width=True,
        )

    with dl_cols[1]:
        # render_excel writes a file; we capture it via tempfile and read bytes
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            render_excel(report, tmp.name)
            tmp_path = Path(tmp.name)
        excel_bytes = tmp_path.read_bytes()
        tmp_path.unlink()
        st.download_button(
            label="⬇ Download Excel",
            data=excel_bytes,
            file_name=f"{proj_name}_design.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with dl_cols[2]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            render_pdf(report, tmp.name)
            tmp_path = Path(tmp.name)
        pdf_bytes = tmp_path.read_bytes()
        tmp_path.unlink()
        st.download_button(
            label="⬇ Download PDF",
            data=pdf_bytes,
            file_name=f"{proj_name}_design.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
