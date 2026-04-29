# Lift Station Streamlit QA/QC App

A local proof-of-concept testing UI for the `nexus_liftstation` calculation engine. **This is a throwaway tool for senior-designer QA/QC**, not a production widget. The real frontend will be built into Nexus separately.

## What it's for

- Sanity-checking the math against real lift stations the senior designer knows
- Spotting bugs at intermediate calculation steps (not just final answers)
- Letting non-Python users poke at variants without writing code
- Testing how the calc engine responds to weird inputs

## What it isn't for

- Production design output (use the Excel/PDF renderers directly for that)
- Anything that needs to persist between sessions
- Anything user-facing or external

## Run it

From the repo root:

```bash
pip install streamlit plotly
streamlit run apps/lift_station_streamlit/app.py
```

A browser tab opens at `http://localhost:8501`. The LS8108 reference example is pre-loaded — hit "Run Design" immediately to see the calc engine produce known-good numbers, then start swapping inputs to test variants.

## Structure

```
apps/lift_station_streamlit/
  app.py              - main Streamlit app (single file)
  ls8108_preset.py    - the reference example used as default state
  README.md           - this file
```

## Notes on what to look for during QA/QC

The app surfaces three things the senior designer should pay attention to:

1. **Yellow banner if a placeholder pump curve is in use.** Operating-point results are bogus until real Flygt cut sheets replace the placeholders.
2. **Cycle-time pass/fail indicators against the spreadsheet's thresholds** (Tmin > 5 min, Tavg run > 2 min, Tavg cycle < 30 min). The thresholds match the spreadsheet's "Check Cycle Times" tab.
3. **An "Intermediate values" expander on every section** that exposes what the spreadsheet would show in its individual cells, so you can spot-check calc-by-calc, not just the final answer.

The two flagged divergences from CMA standards (cycle time formula in `calc/cycle_time.py`, single-case buoyancy in `calc/buoyancy.py`) are noted in the results panel each run.
