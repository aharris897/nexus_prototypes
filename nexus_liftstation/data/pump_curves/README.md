# Pump Curve CSV Format

This directory holds bundled pump-curve data. Files with `_PLACEHOLDER` in
the filename are NOT real manufacturer data — they are plausibly-shaped
synthetic curves used during prototype development. Replace with real
cut-sheet data before any production use.

## CSV format

Header row required. Columns:

| Column | Required | Units | Notes |
|---|---|---|---|
| `flow_gpm` | yes | gallons per minute | Must be sorted ascending |
| `head_ft` | yes | feet of water column | Total dynamic head produced by pump at this flow |
| `efficiency_pct` | no | percent | Wire-to-water efficiency at this point |
| `npshr_ft` | no | feet | NPSH-required at this point |

If `efficiency_pct` or `npshr_ft` are present in any row, they should be
present in every row for clean PCHIP interpolation.

## Recommended density

15–25 points spanning the full Q–H curve, with extra resolution near
the preferred operating region. PCHIP handles non-uniform spacing well.

## Filename convention

```
<manufacturer>_<model>_<size>_<optional_PLACEHOLDER>.csv
```

Examples:
- `flygt_ns3127_med_PLACEHOLDER.csv` (synthetic placeholder)
- `flygt_ns3127_205mm.csv` (real cut sheet, 205 mm impeller trim)

The `is_placeholder` flag on `PumpCurve` is set automatically based on
whether `PLACEHOLDER` appears in the filename.

## Where real curves come from

Contact a Xylem / Flygt sales rep and request engineering cut sheets.
Typical municipal sanitary-sewer lift stations use 3000-series N-pumps:
NS 3085, NS 3127, NS 3153, NS 3171, NS 3202, NS 3301.
