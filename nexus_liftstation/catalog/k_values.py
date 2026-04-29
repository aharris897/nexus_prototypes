"""K-value (resistance coefficient) reference table.

Mirrors the 'K-Value' tab in the CMA Lift Station Calculations Template.
Used for fitting head-loss calculations: hf = K * v^2 / (2g).

These values are sized by nominal pipe diameter (inches) and follow the
Crane TP-410 / equivalent-length convention (L/D ratio).

Source: K values come directly from the CMA spreadsheet K-Value tab.
The senior designer should cross-check against current Crane TP-410
or HI standards if any specific value is in question.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Pipe size column headers (inches). The spreadsheet K-Value tab uses
#: nominal-size buckets; we represent each bucket by its upper bound for
#: ease of lookup.
_PIPE_SIZE_BUCKETS: list[tuple[float, str]] = [
    (0.5, '1/2"'),
    (0.75, '3/4"'),
    (1.0, '1"'),
    (1.25, '1-1/4"'),
    (1.5, '1-1/2"'),
    (2.0, '2"'),
    (3.0, '2-1/2" - 3"'),
    (4.0, '4"'),
    (6.0, '6"'),
    (10.0, '8" - 10"'),
    (16.0, '12" - 16"'),
    (24.0, '18" - 24"'),
]


@dataclass(frozen=True)
class KValueRow:
    """One fitting type, with K values across nominal pipe sizes."""

    name: str
    description: str
    #: K values by pipe-size bucket index (parallel to _PIPE_SIZE_BUCKETS).
    k_values: tuple[float, ...]


# K values transcribed from CMA spreadsheet K-Value tab. Each row's tuple
# corresponds to the buckets defined in _PIPE_SIZE_BUCKETS.
_ROWS: list[KValueRow] = [
    KValueRow(
        "Gate Valve", "Standard gate valve, fully open",
        (0.22, 0.20, 0.18, 0.18, 0.15, 0.15, 0.14, 0.14, 0.12, 0.11, 0.10, 0.10),
    ),
    KValueRow(
        "Globe Valve", "Standard globe valve",
        (9.20, 8.50, 7.80, 7.50, 7.10, 6.50, 6.10, 5.80, 5.10, 4.80, 4.40, 4.10),
    ),
    KValueRow(
        "Ball Valve", "Standard ball valve",
        (0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.05, 0.05, 0.05, 0.04, 0.04, 0.04),
    ),
    KValueRow(
        "Plug Valve Straightaway", "Plug valve, straight flow",
        (0.48, 0.45, 0.41, 0.40, 0.38, 0.34, 0.32, 0.31, 0.27, 0.25, 0.23, 0.22),
    ),
    KValueRow(
        "Standard Elbow 90", "90 degree standard elbow",
        (0.81, 0.75, 0.69, 0.66, 0.63, 0.57, 0.54, 0.51, 0.45, 0.42, 0.39, 0.36),
    ),
    KValueRow(
        "Standard Elbow 45", "45 degree standard elbow",
        (0.43, 0.40, 0.37, 0.35, 0.34, 0.30, 0.29, 0.27, 0.24, 0.22, 0.21, 0.19),
    ),
    KValueRow(
        "Long Radius Elbow 90", "90 degree long-radius elbow",
        (0.43, 0.40, 0.37, 0.35, 0.34, 0.30, 0.29, 0.27, 0.24, 0.22, 0.21, 0.19),
    ),
    KValueRow(
        "Standard Tee Thru-Flow", "Standard tee, run/through flow",
        (0.54, 0.50, 0.46, 0.44, 0.42, 0.38, 0.36, 0.34, 0.30, 0.28, 0.26, 0.24),
    ),
    KValueRow(
        "Standard Tee Thru-Branch", "Standard tee, branch flow",
        (1.62, 1.50, 1.38, 1.32, 1.26, 1.14, 1.08, 1.02, 0.90, 0.84, 0.78, 0.72),
    ),
    KValueRow(
        "Pipe Bend r/d=1", "Pipe bend, ratio of bend radius to diameter = 1",
        (0.54, 0.50, 0.46, 0.44, 0.42, 0.38, 0.36, 0.34, 0.30, 0.28, 0.26, 0.24),
    ),
    KValueRow(
        "Pipe Bend r/d=2", "Pipe bend, r/d = 2",
        (0.32, 0.30, 0.28, 0.26, 0.25, 0.23, 0.22, 0.20, 0.18, 0.17, 0.16, 0.14),
    ),
    KValueRow(
        "Swing Check Valve",
        "Swing check valve at min full-disc-lift velocity (LD=100)",
        (2.70, 2.50, 2.30, 2.20, 2.10, 1.90, 1.80, 1.70, 1.50, 1.40, 1.30, 1.20),
    ),
    KValueRow(
        "Reducer", "Standard concentric reducer (typical CMA value)",
        # The spreadsheet hardcodes 0.41 for the LS8108 example without a
        # direct K-Value tab cross-reference; we expose 0.41 as the default
        # for all sizes here. Senior designer should verify against the
        # specific reducer geometry.
        (0.41,) * 12,
    ),
    KValueRow(
        "Pipe Exit Projecting", "Pipe exit, projecting",
        (1.00,) * 12,
    ),
    KValueRow(
        "Pipe Entrance Sharp-Edged", "Pipe entrance, sharp-edged",
        (0.50,) * 12,
    ),
    KValueRow(
        "Pipe Entrance Inward Projecting", "Pipe entrance, inward projecting",
        (0.78,) * 12,
    ),
]


def _bucket_index_for_diameter(nominal_diameter_in: float) -> int:
    """Return the index into _PIPE_SIZE_BUCKETS for a given nominal size."""
    for i, (upper, _label) in enumerate(_PIPE_SIZE_BUCKETS):
        if nominal_diameter_in <= upper:
            return i
    return len(_PIPE_SIZE_BUCKETS) - 1


def get_k_value(fitting_name: str, nominal_diameter_in: float) -> float:
    """Look up K for a fitting at a given nominal pipe size.

    Args:
        fitting_name: Must match a name in the loaded table (case-insensitive).
        nominal_diameter_in: Pipe nominal diameter in inches.

    Returns:
        K-value (dimensionless).

    Raises:
        KeyError: If the fitting name is not in the table.
    """
    name_lower = fitting_name.strip().lower()
    for row in _ROWS:
        if row.name.lower() == name_lower:
            idx = _bucket_index_for_diameter(nominal_diameter_in)
            return row.k_values[idx]
    raise KeyError(
        f"Fitting '{fitting_name}' not found in K-value table. "
        f"Available: {[r.name for r in _ROWS]}"
    )


def list_fittings() -> list[str]:
    """List all fitting names available in the K-value table."""
    return [r.name for r in _ROWS]


def all_rows() -> list[KValueRow]:
    """Return all rows (for the Excel renderer to dump the K-value tab)."""
    return list(_ROWS)


def pipe_size_buckets() -> list[tuple[float, str]]:
    """Return the pipe-size buckets used by the K-value table."""
    return list(_PIPE_SIZE_BUCKETS)
