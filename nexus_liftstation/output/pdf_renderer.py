"""PDF design report renderer.

Produces a multi-page calculation report mirroring the CMA Order of
Operations narrative. Uses ReportLab Platypus for portability.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..calc.design import DesignReport


def _make_section(title: str, styles) -> Paragraph:
    return Paragraph(title, styles["Heading2"])


def _make_subsection(title: str, styles) -> Paragraph:
    return Paragraph(title, styles["Heading3"])


def _make_table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(rows, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#305496")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ]
        )
    )
    return t


def _fmt(value, decimals: int = 2) -> str:
    """Format a numeric value, handling None and NaN cleanly."""
    if value is None:
        return "—"
    if isinstance(value, float):
        if value != value:  # NaN
            return "—"
        return f"{value:,.{decimals}f}"
    return str(value)


def _system_curve_drawing(report: DesignReport) -> Drawing | None:
    """Build a small system/pump curve chart using ReportLab graphics."""
    if report.tdh_curve is None:
        return None

    flows = report.tdh_curve.flows_gpm()
    sys_h = report.tdh_curve.tdh_ft()

    drawing = Drawing(450, 220)
    chart = HorizontalLineChart()
    chart.x = 50
    chart.y = 30
    chart.height = 160
    chart.width = 360

    data = [list(zip(flows, sys_h))]
    series_names = ["System Curve"]

    if report.selected_pump is not None:
        pump_h = []
        for q in flows:
            ph = report.selected_pump.head_at(q)
            pump_h.append(ph if ph == ph else 0.0)
        data.append(list(zip(flows, pump_h)))
        series_names.append(f"Pump: {report.selected_pump.model}")

    # ReportLab's HorizontalLineChart doesn't take XY data directly; need
    # to set categoryAxis. Simpler to just plot as Y values vs index.
    chart.data = [sys_h]
    if report.selected_pump is not None:
        pump_h = []
        for q in flows:
            ph = report.selected_pump.head_at(q)
            pump_h.append(ph if ph == ph else 0.0)
        chart.data.append(pump_h)

    chart.categoryAxis.categoryNames = [
        f"{int(q)}" if i % 4 == 0 else "" for i, q in enumerate(flows)
    ]
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.lines[0].strokeColor = colors.HexColor("#1F4E78")
    chart.lines[0].strokeWidth = 1.5
    if report.selected_pump is not None:
        chart.lines[1].strokeColor = colors.HexColor("#C00000")
        chart.lines[1].strokeWidth = 1.5

    drawing.add(chart)
    legend = Legend()
    legend.x = 320
    legend.y = 200
    legend.alignment = "right"
    legend.fontName = "Helvetica"
    legend.fontSize = 8
    legend.colorNamePairs = [
        (colors.HexColor("#1F4E78"), "System Curve"),
    ]
    if report.selected_pump is not None:
        legend.colorNamePairs.append(
            (colors.HexColor("#C00000"), f"Pump: {report.selected_pump.model}")
        )
    drawing.add(legend)
    return drawing


def render_pdf(report: DesignReport, path: Path | str) -> Path:
    """Render a DesignReport as a PDF design report."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(p),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=16,
    )
    note_style = ParagraphStyle(
        "note",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#800000"),
        leftIndent=12,
    )

    story = []

    # --- Title page -------------------------------------------------------
    story.append(Paragraph("Lift Station Design Report", title_style))
    proj = report.project
    story.append(Paragraph(f"<b>Project:</b> {proj.project_name or '—'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Location:</b> {proj.project_location or '—'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Project No:</b> {proj.project_number or '—'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Designer:</b> {proj.designer or '—'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Station:</b> {proj.geometry.station_number}", styles["Normal"]))
    story.append(Spacer(1, 12))

    if report.notes:
        story.append(_make_subsection("Design Notes & Warnings", styles))
        for note in report.notes:
            story.append(Paragraph("&bull; " + note, note_style))
        story.append(Spacer(1, 12))

    # --- Step 1: Flow Estimate -------------------------------------------
    story.append(_make_section("Step 1 - Estimated Sewage Inflows (FAC 64E-6.008)", styles))
    if report.flow_estimate is not None:
        rows = [["Structure / Land Use", "Units", "GPD/Unit", "ADF (GPD)"]]
        for item in report.flow_estimate.line_items:
            rows.append([
                item.description,
                _fmt(item.number_of_units, 0),
                _fmt(item.flow_per_unit_gpd, 0),
                _fmt(item.average_daily_flow_gpd, 0),
            ])
        rows.append(["TOTAL", "", "",
                    _fmt(report.flow_estimate.average_daily_flow_gpd, 0)])
        story.append(_make_table(rows, [3.6 * inch, 0.9 * inch, 1.0 * inch, 1.2 * inch]))
        story.append(Paragraph(
            f"Service Area Population: <b>{_fmt(report.flow_estimate.service_area_population, 0)}</b>",
            styles["Normal"]))
    else:
        story.append(Paragraph("No inflows provided.", styles["Italic"]))
    story.append(Spacer(1, 12))

    # --- Step 2: Peak Factor + Design Flow --------------------------------
    story.append(_make_section("Step 2 - Design Pumping Flow Rate", styles))
    if report.pumping_flow is not None:
        pf = report.pumping_flow
        rows = [
            ["Item", "Value"],
            ["Average Daily Flow (GPD)", _fmt(pf.average_daily_flow_gpd, 0)],
            ["Tiered Table Peak Factor", _fmt(pf.peak_factor_result.table_pf, 2)],
            ["Fair-Geyer Peak Factor", _fmt(pf.peak_factor_result.fair_geyer_pf, 4)],
            ["Design Peak Factor (greater of two)", _fmt(pf.peak_factor_result.design_pf, 4)],
            ["Governing Method", pf.peak_factor_result.governing_method],
            ["Peak Flow (GPD)", _fmt(pf.peak_flow_gpd, 0)],
            ["Minimum Pumping Rate (GPM)", _fmt(pf.minimum_pumping_rate_gpm, 2)],
            ["Recommended Design Pumping Rate (GPM, rounded up to 100)",
             _fmt(pf.recommended_pumping_rate_gpm, 0)],
        ]
        story.append(_make_table(rows, [4.5 * inch, 2.0 * inch]))
    story.append(Spacer(1, 12))

    # --- Step 3: Wet Well + Cycle Times -----------------------------------
    story.append(PageBreak())
    story.append(_make_section("Step 3 - Wet Well & Cycle Times", styles))
    if report.wet_well_volume is not None:
        v = report.wet_well_volume
        rows = [
            ["Wet Well Parameter", "Value"],
            ["Diameter (ft)", _fmt(v.diameter_ft, 2)],
            ["Lead Pump On Elev (ft)", _fmt(v.lead_pump_on_el_ft, 2)],
            ["Both Pumps Off Elev (ft)", _fmt(v.both_pumps_off_el_ft, 2)],
            ["Working Depth (ft)", _fmt(v.working_depth_ft, 2)],
            ["Working Volume (gal)", _fmt(v.volume_gal, 1)],
        ]
        story.append(_make_table(rows, [3.0 * inch, 2.0 * inch]))
        story.append(Spacer(1, 6))

    if report.cycle_times is not None:
        ct = report.cycle_times
        rows = [
            ["Cycle Time Check", "Value (min)", "Spec"],
            ["Tmin = 4V/Qpump", _fmt(ct.t_min_min, 2), ">5 min"],
            ["Tavg run = V/(Qpeak-Qavg)", _fmt(ct.t_avg_run_min, 2), ">2 min"],
            ["Tavg cycle = Tavg run + V/Qavg", _fmt(ct.t_avg_cycle_min, 2), "<30 min"],
            ["Tpeak run = V/(Qpump-Qpeak)", _fmt(ct.t_peak_run_min, 2), "—"],
            ["Tpeak cycle = Tpeak run + V/Qpeak", _fmt(ct.t_peak_cycle_min, 2), "—"],
        ]
        story.append(_make_table(rows, [3.4 * inch, 1.4 * inch, 1.2 * inch]))
        story.append(Paragraph(
            "Note: Tavg formulas use (Qpeak-Qavg) per CMA spreadsheet; "
            "this diverges from textbook (Qpump-Qavg).",
            note_style))
    story.append(Spacer(1, 12))

    # --- Step 4: Static Head ---------------------------------------------
    story.append(_make_section("Step 4 - Static Head Components", styles))
    if report.static_head is not None:
        sh = report.static_head
        rows = [
            ["Component", "Value (ft)"],
            ["Destination Elevation", _fmt(sh.destination_elevation_ft, 2)],
            ["Pump Off Elevation", _fmt(sh.pump_off_elevation_ft, 2)],
            ["Static Lift", _fmt(sh.static_lift_ft, 2)],
            [f"Static Head at Connection ({_fmt(sh.static_head_at_connection_psi, 2)} psi)",
             _fmt(sh.static_head_at_connection_ft, 2)],
            ["TOTAL STATIC HEAD", _fmt(sh.total_static_head_ft, 2)],
        ]
        story.append(_make_table(rows, [4.0 * inch, 1.5 * inch]))
    story.append(Spacer(1, 12))

    # --- Step 5: TDH Curve -----------------------------------------------
    story.append(PageBreak())
    story.append(_make_section("Step 5 - Total Dynamic Head Curve", styles))
    if report.tdh_curve is not None:
        rows = [["Flow (GPM)", "Static (ft)"]]
        for seg in report.tdh_curve.segments:
            rows[0].append(f"Seg {seg.label} loss (ft)")
        rows[0].append("TDH (ft)")
        if report.selected_pump is not None:
            rows[0].append(f"Pump Head (ft)")

        # Show every 4th point to keep the table compact
        for i, pt in enumerate(report.tdh_curve.points):
            if i % 4 != 0 and i != len(report.tdh_curve.points) - 1:
                continue
            row = [_fmt(pt.flow_gpm, 0), _fmt(pt.static_head_ft, 2)]
            for seg_loss in pt.segment_losses:
                row.append(_fmt(seg_loss.total_loss_ft, 3))
            row.append(_fmt(pt.total_dynamic_head_ft, 2))
            if report.selected_pump is not None:
                ph = report.selected_pump.head_at(pt.flow_gpm)
                row.append(_fmt(ph, 2))
            rows.append(row)
        col_count = len(rows[0])
        col_widths = [6.5 * inch / col_count] * col_count
        story.append(_make_table(rows, col_widths))
    story.append(Spacer(1, 12))

    # --- Step 6: System & Pump Curves chart -------------------------------
    story.append(_make_section("Step 6 - System and Pump Curves", styles))
    chart_drawing = _system_curve_drawing(report)
    if chart_drawing is not None:
        story.append(chart_drawing)
    if report.operating_point is not None:
        op = report.operating_point
        story.append(Spacer(1, 6))
        rows = [
            ["Operating Point", "Value"],
            ["Pump Model", op.pump_model + (" (PLACEHOLDER)" if op.is_placeholder else "")],
            ["Operating Flow (GPM)", _fmt(op.flow_gpm, 1)],
            ["Operating Head (ft)", _fmt(op.head_ft, 2)],
            ["Efficiency (%)", _fmt(op.efficiency_pct, 1)],
            ["NPSH Required (ft)", _fmt(op.npshr_ft, 2)],
            ["Offset from target design GPM", _fmt(op.gpm_offset_from_target, 1)],
        ]
        story.append(_make_table(rows, [3.0 * inch, 3.0 * inch]))
    story.append(Spacer(1, 12))

    # --- Step 7: Buoyancy -------------------------------------------------
    if report.buoyancy is not None:
        story.append(PageBreak())
        story.append(_make_section("Step 7 - Buoyancy Check (single-case)", styles))
        b = report.buoyancy
        rows = [
            ["Buoyancy Parameter", "Value"],
            ["Outside Diameter (ft)", _fmt(b.outside_diameter_ft, 2)],
            ["Height of Structure (ft)", _fmt(b.height_of_structure_ft, 2)],
            ["Tremie Seal Height (ft)", _fmt(b.tremie_seal_height_ft, 2)],
            ["Volume Displaced (CF)", _fmt(b.volume_displaced_cf, 1)],
            ["Buoyant Force (lb)", _fmt(b.buoyant_force_lb, 0)],
            ["Total Resisting Weight (lb)", _fmt(b.total_weight_lb, 0)],
            ["Weight / Buoyancy Ratio", _fmt(b.weight_to_buoyancy_ratio, 3)],
            ["Pass Check", "OK" if b.passes_check else "NOT OK"],
        ]
        story.append(_make_table(rows, [3.5 * inch, 2.0 * inch]))
        story.append(Paragraph(
            "DIVERGENCE: Single-case calc only; CMA Notes 22 & 23 require "
            "two load cases. Senior designer review required.",
            note_style))

    doc.build(story)
    return p
