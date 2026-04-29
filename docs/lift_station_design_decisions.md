# Design Decisions Report

**Project:** `nexus_liftstation`
**Date:** 2026-04-28
**Audience:** Senior CMA designer iterating on this scaffold toward a web widget

This report documents the architectural decisions, engineering judgment calls, and debugs encountered while building the prototype. Read this before iterating on the codebase.

---

## 1. Scope decisions (locked at start of build)

| Decision | Choice | Rationale |
|---|---|---|
| **Architecture** | Python library + thin FastAPI wrapper | Library is the source of truth and unit-testable in isolation. FastAPI gives the front-end engineer a clean HTTP contract with auto-generated OpenAPI docs. |
| **License** | MIT | Permissive default. CMA legal/management should swap if internal license is required. |
| **Python version** | 3.11+ | Modern typing (`X \| Y` unions), `dataclasses`, well-supported by all dependencies. |
| **Test framework** | pytest | Standard, low ceremony, runs the regression test in <2 seconds. |
| **Type checker** | mypy, permissive | Keeps the scaffold flexible during early iteration. The senior designer can tighten settings (`disallow_untyped_defs`, `strict_optional`) later. |
| **Outputs** | JSON + Excel + PDF, separated as 3 renderers | Each output has different strengths and audiences. JSON is the wire format for the web widget; Excel is what the senior designer review process expects; PDF is for permitting/client deliverables. |
| **Pump curve interpolation** | scipy PCHIP | Real pump curves don't fit low-order polynomials cleanly and a regular cubic spline can wiggle. PCHIP is monotonicity-preserving, which matches physical pump-curve behavior. CSVs are easily editable by non-programmers. |
| **Peak factor** | Compute BOTH methods always | Either could govern depending on ADF vs population shape. Reporting both makes the design defensible during review. |
| **FAC 64E-6.008 Table I** | Curated subset (22 entries) | Full table has dozens of rows; senior designer can extend `catalog/fac_64e_6_008_table_i.py` `ENTRIES` dict as needed. |
| **Pump catalog** | Hybrid: bundled placeholders + user CSV upload | Real Flygt cut sheets aren't bundled (see Decision #3 below). The CSV interface lets the senior designer drop in real data without touching code. |
| **Buoyancy** | Replicate spreadsheet's single-case behavior | Per user direction (`backend should go off what the spreadsheet has`). Flagged with DIVERGENCE NOTE for review. |

---

## 2. Verification status

The library reproduces the LS8108 reference example (from `Parameters_needed_for_Pump_Lift_Station_Design.pdf`) and the CMA spreadsheet's stored example values:

| Quantity | Library result | Reference | Match |
|---|---|---|---|
| Average Daily Flow | 103,658 GPD | 103,658 GPD (PDF) | exact |
| Service Area Population | 832.5 | 833 (PDF rounded) | exact (unrounded) |
| Fair-Geyer Peak Factor | 3.8499 | 3.85 (PDF) | exact |
| Design Peak Factor (governing) | 3.8499 (Fair-Geyer) | 3.85 | exact |
| Peak Flow | 399,075.26 GPD | 399,075.26 (sheet) | exact |
| Min Pumping Rate | 277.1356 GPM | 277.14 (PDF) | exact |
| Design Pumping Rate | 300 GPM | 300 (PDF) | exact |
| Total Static Head | 42.9523 ft | 42.95233 (sheet) | exact |
| TDH at 0/60/120/240/480/1200/2400 GPM | matches | matches | ~1e-14 floating-point error |
| Pipe velocity at 60 GPM (6" segment A) | 0.6808297348811447 ft/s | matches sheet | exact |
| Wet well working volume | 2349.911304885166 gal | matches sheet | exact |
| Tmin | 93.9965 min | 93.99645 | exact |
| Tavg run | 89.9327 min | 89.93267 | exact |
| Tavg cycle | 315.5242 min | 315.52416 | exact |
| Tpeak run | 37.0335 min | 37.03350 | exact |
| Tpeak cycle | 101.3330 min | 101.33300 | exact |

All 39 unit tests pass (`pytest tests/`). All 27 formulas in the generated Excel output recalculate cleanly with zero errors (verified with LibreOffice headless).

---

## 3. Pump-curve digitization decision

**Decision:** Bundled curves are PLACEHOLDERS only; senior designer must obtain real cut sheets from a Flygt rep before production use.

**Why:** The marketing brochure provided (`fb199-ca_flygt_sub_brochure_sm2.pdf`) was reviewed but determined to be unsuitable for engineering digitization:

1. **Resolution problem.** Curves are small thumbnails — multiple impeller codes crammed onto one chart. Reading values to better than ±5–15% accuracy is not realistic.
2. **Missing curves.** Real cut sheets show efficiency, NPSH-required, and power/BHP curves alongside the Q-H curve. The brochure shows only Q-H.
3. **Wrong product family.** The brochure focuses on dewatering and slurry pumps for construction, mining, and quarry applications. Municipal sanitary lift stations need 3000-series N-pumps. The brochure's NS-series pages (NS 3085, NS 3127, NS 3153, NS 3171, NS 3202, NS 3301) are the relevant subset, but their curves are still thumbnail-quality.
4. **No specific impeller trim labels.** Real designs require the specific trim diameter; brochure uses impeller code numbers without trim values.

**What got bundled:** Three plausibly-shaped placeholder CSVs matching the rough Q/H envelopes of small / medium / large municipal pumps:
- `flygt_ns3085_small_PLACEHOLDER.csv`: 0–600 GPM, 45 ft → 10 ft
- `flygt_ns3127_med_PLACEHOLDER.csv`: 0–1500 GPM, 85 ft → 20 ft
- `flygt_ns3171_large_PLACEHOLDER.csv`: 0–2400 GPM, 120 ft → 30 ft

Each curve includes synthetic efficiency and NPSH-required so the operating-point logic exercises those code paths.

**Path forward:** Senior designer or project manager contacts Xylem / Flygt sales rep, requests engineering cut sheets for the specific pump models CMA commonly specs, transcribes (or asks the rep for digital data) into the same CSV format, and either drops into `data/pump_curves/` or uploads via `POST /catalog/pumps/upload`.

---

## 4. Divergences flagged for senior designer review

These are places where the spreadsheet's behavior differs from a textbook reference or from CMA's stated standard detail. Per user direction, the spreadsheet behavior was replicated verbatim, with `DIVERGENCE NOTE` comments in code and notes propagated into the Excel and PDF outputs.

### 4.1 Cycle-time `Tavg run` formula uses `(Qpeak - Qavg)` instead of `(Qpump - Qavg)`

**Where:** `nexus_liftstation/calc/cycle_time.py`, function `cycle_times`.

**Spreadsheet formula:** `D44 = D32/(D37-D36) = V / (Qpeak - Qavg)` (cells from `Pump Cycle Times` tab).

**Textbook (PDF section 6.3.9.1):** `T = V/Q_in + V/(Q_out - Q_in)` where `Q_out` = pump output rate.

**My initial implementation** used the textbook form and got `Tavg run = 26.23 min` against the spreadsheet's `89.93 min` for the LS8108 example. After examining the spreadsheet formulas directly, switched to the spreadsheet form per user direction.

**Possible explanations the senior designer might consider:**
- The spreadsheet's "Tavg run" might be intended as something other than the textbook quantity (e.g., run time at average inflow during a peak event in a multi-pump station with pump cycling).
- The spreadsheet may simply contain a long-standing error.
- The label may be defining a different quantity than the textbook.

**Recommendation:** Discuss internally and either (a) confirm the spreadsheet form is correct and update the textbook reference, or (b) switch to the textbook form and update the LS8108 regression-test expected values.

### 4.2 Buoyancy is single-case; CMA Notes 22 & 23 require two load cases

**Where:** `nexus_liftstation/calc/buoyancy.py`.

**Spreadsheet behavior (replicated):** Single load case with 1.1 safety factor on buoyancy and `total weight = walls + tremie seal at concrete density`. The "omitting skin friction" note in cell `E21` is preserved as documentation.

**CMA standard detail:** Two separate buoyancy load cases:
- 25-year construction stage (no top slab, partial structure)
- 100-year final stage (with secondary pour)

…and explicitly excludes top slab, secondary pour, pumps, and skin friction from resisting weight in certain checks.

**Recommendation:** Senior designer should add the second load case before any production use. The data classes already accept the relevant geometry inputs (top slab thickness, second pour wall height) so extending `buoyancy_check` to return both cases is straightforward.

---

## 5. Build-time debugs

Issues encountered during the build, in chronological order, with resolution:

| # | Issue | Resolution |
|---|---|---|
| 1 | Initial textbook-form cycle-time formulas produced `Tavg run = 26.23 min` vs spreadsheet's `89.93 min` (a ~70 min discrepancy). | Inspected spreadsheet cell formulas directly with openpyxl in `data_only=False` mode, discovered `D44 = D32/(D37-D36)` uses Qpeak-Qavg. Switched to spreadsheet form; flagged with DIVERGENCE NOTE; documented in this report. |
| 2 | `bash` brace expansion (`mkdir -p src/foo/{bar,baz}`) failed in container shell, leaving a literal directory named `{bar,baz}`. | Cleaned up with `rm -rf` and used explicit space-separated `mkdir` calls. |
| 3 | `7.48051948` (true gallons-per-cubic-foot) vs spreadsheet's truncated `7.48`. | Matched spreadsheet's `7.48` verbatim for regression-test parity. Flagged in `constants.py` with explanatory comment. |
| 4 | Spreadsheet uses `62.43 lb/ft³` for water density in the buoyancy tab but `62.37 lb/ft³` in the TDH tab. | Both preserved exactly to match each respective tab's stored values. Flagged in `constants.py` and `calc/buoyancy.py`. |
| 5 | LS8108 PDF shows `833` for service-area population; library computes `832.5` (333 SFH × 2.5). | Difference is invisible at the 4-decimal precision Fair-Geyer needs (`(18+sqrt(0.832))/(4+sqrt(0.832)) ≈ (18+sqrt(0.833))/(4+sqrt(0.833))`). Library keeps the unrounded value for downstream precision. PDF displayed-value is just rounded. |
| 6 | `Reducer` K-value: spreadsheet hardcodes `0.41` in the LS8108 example without an obvious K-Value tab cross-reference. | Exposed `0.41` as the default K for all sizes in `catalog/k_values.py` with a caveat comment. Senior designer should verify against specific reducer geometry. |
| 7 | First `present_files`-style end-to-end run had no `__init__.py` in any subpackage, so imports failed. | Created `__init__.py` for each of `calc/`, `catalog/`, `output/`, `api/`. |
| 8 | FastAPI `UploadFile` parameter required `python-multipart` for runtime smoke tests. | Added `python-multipart` to `[api]` extras in `pyproject.toml`. |
| 9 | The PDF `_system_curve_drawing` helper initially built XY-pair data, but ReportLab's `HorizontalLineChart` expects Y-only series with separate category axis. | Switched to category-axis form with sparse axis labels. |
| 10 | Excel tab "Pump Cycle Times" had a label collision: my formula referenced `B4` (diameter) and `B11`/`B12` (lead-pump-on / both-pumps-off elevations), but the row offsets didn't quite match between layout and formula refs. | Re-derived row numbers from the actual emitted layout and verified the recalculated formulas: `Working Volume = 2349.911 gal` exactly matches the stored value. |

---

## 6. Where to extend next

In rough priority order:

1. **Add the second buoyancy load case** per CMA Notes 22 & 23. The data flow is in place; only `calc/buoyancy.py` needs extending.
2. **Resolve the cycle-time divergence** with engineering review and update either the calc or the docstring to reflect the agreed interpretation.
3. **Get real Flygt cut sheets** from a Xylem rep and replace the placeholder pump CSVs.
4. **Extend FAC 64E-6.008 Table I** in `catalog/fac_64e_6_008_table_i.py` with any structure types CMA frequently encounters that aren't in the curated subset.
5. **Tighten mypy** to `strict = true` once the API surface stabilizes.
6. **Add multi-pump/duty-standby logic** — the current cycle-time module assumes a single duty pump; CMA designs typically include lead/lag with alternation.
7. **Consider adding a permitted-by-FDEP header block** to the PDF renderer — Florida permitting reviewers expect specific signature/seal blocks.

---

## 7. Files and how they map to the CMA spreadsheet

| Spreadsheet tab | Module(s) |
|---|---|
| Project Data | `models.LiftStationProject` (project_name, project_location, project_number, designer fields) |
| Flow Calculations | `calc/flow.py` + `catalog/fac_64e_6_008_table_i.py` |
| Flow Rate | `calc/peak_factor.py` |
| Pump Cycle Times | `calc/cycle_time.py` (volume + 5 cycle checks) |
| Headloss Fitting | `calc/head_loss.py::static_head` + per-segment fitting roll-up |
| TDH | `calc/head_loss.py::build_tdh_curve` |
| System Curves | `calc/pump_match.py::find_operating_point`; chart in Excel renderer |
| Buoyancy (Tremie) | `calc/buoyancy.py` (single-case, with DIVERGENCE NOTE) |
| K-Value | `catalog/k_values.py` |
| (no analog in spreadsheet) | `calc/design.py` orchestrator that ties all of the above together |

---

## 8. How to read this codebase

If you're new to the repo and want to understand it fast:

1. Read `README.md`.
2. Read `examples/ls8108_example.py` — the entire workflow in ~100 lines.
3. Open `tests/test_ls8108_regression.py` — see the exact numbers each module is expected to produce.
4. Browse `calc/design.py` — the orchestrator showing how the pieces compose.
5. Spot-check `calc/cycle_time.py` and `calc/buoyancy.py` for the DIVERGENCE NOTEs.
