"""Pump curve representation, interpolation, and catalog loading.

Pump curves are stored as point-by-point CSV files (Q, H, optional
efficiency, optional NPSHr). Interpolation uses scipy's PCHIP (Piecewise
Cubic Hermite Interpolating Polynomial), which preserves monotonicity
between points and avoids the wiggles a regular cubic spline can
introduce on a noisy or near-linear pump curve.

CSV format (header row required):
    flow_gpm, head_ft, efficiency_pct, npshr_ft

Only flow_gpm and head_ft are required; the other two are optional.

PLACEHOLDER WARNING:
The curves bundled in data/pump_curves/ are NOT real manufacturer data.
They are plausibly-shaped placeholder curves for development/testing.
Replace with real Flygt cut-sheet data before production use.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator


@dataclass(frozen=True)
class PumpCurvePoint:
    """One operating point on a pump curve."""

    flow_gpm: float
    head_ft: float
    efficiency_pct: float | None = None
    npshr_ft: float | None = None


@dataclass
class PumpCurve:
    """A complete pump curve with metadata.

    Attributes:
        manufacturer: Pump manufacturer (e.g. 'Flygt').
        model: Pump model designation.
        impeller_code: Specific impeller code or trim if applicable.
        speed_rpm: Pump speed (RPM); None if N/A.
        is_placeholder: True if this is bundled placeholder data, NOT real
            manufacturer data. Set automatically by the catalog loader for
            files in data/pump_curves/.
        points: Sorted list of operating points.
    """

    manufacturer: str
    model: str
    impeller_code: str = ""
    speed_rpm: float | None = None
    is_placeholder: bool = False
    points: list[PumpCurvePoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError(
                f"Pump curve {self.manufacturer} {self.model} has no points."
            )
        self.points = sorted(self.points, key=lambda p: p.flow_gpm)
        self._head_interp: PchipInterpolator | None = None
        self._eff_interp: PchipInterpolator | None = None
        self._npshr_interp: PchipInterpolator | None = None

    def _build_interpolators(self) -> None:
        if self._head_interp is not None:
            return
        flows = np.array([p.flow_gpm for p in self.points])
        heads = np.array([p.head_ft for p in self.points])
        self._head_interp = PchipInterpolator(flows, heads, extrapolate=False)

        eff_data = [p.efficiency_pct for p in self.points]
        if all(e is not None for e in eff_data):
            self._eff_interp = PchipInterpolator(
                flows, np.array(eff_data, dtype=float), extrapolate=False
            )

        npshr_data = [p.npshr_ft for p in self.points]
        if all(n is not None for n in npshr_data):
            self._npshr_interp = PchipInterpolator(
                flows, np.array(npshr_data, dtype=float), extrapolate=False
            )

    def head_at(self, flow_gpm: float) -> float:
        """Return interpolated head (ft) at a given flow.

        Returns NaN for flow values outside the bundled range (no extrapolation).
        """
        self._build_interpolators()
        assert self._head_interp is not None
        result = float(self._head_interp(flow_gpm))
        return result

    def efficiency_at(self, flow_gpm: float) -> float | None:
        """Return interpolated efficiency (%), or None if not available."""
        self._build_interpolators()
        if self._eff_interp is None:
            return None
        return float(self._eff_interp(flow_gpm))

    def npshr_at(self, flow_gpm: float) -> float | None:
        """Return interpolated NPSH-required (ft), or None if not available."""
        self._build_interpolators()
        if self._npshr_interp is None:
            return None
        return float(self._npshr_interp(flow_gpm))

    @property
    def flow_min_gpm(self) -> float:
        return self.points[0].flow_gpm

    @property
    def flow_max_gpm(self) -> float:
        return self.points[-1].flow_gpm


# --- CSV loader -------------------------------------------------------------


def load_curve_from_csv(
    path: Path | str,
    manufacturer: str = "",
    model: str = "",
    impeller_code: str = "",
    speed_rpm: float | None = None,
    is_placeholder: bool = False,
) -> PumpCurve:
    """Load a pump curve from a CSV file.

    The CSV must have a header row with columns including 'flow_gpm' and
    'head_ft'. Optional columns: 'efficiency_pct', 'npshr_ft'.

    Args:
        path: Path to the CSV file.
        manufacturer: Manufacturer name (overrides nothing in CSV; metadata).
        model: Model name (metadata).
        impeller_code: Impeller code (metadata).
        speed_rpm: Pump speed (metadata).
        is_placeholder: Whether to mark this as placeholder data.

    Returns:
        A PumpCurve.

    Raises:
        FileNotFoundError: If the CSV doesn't exist.
        ValueError: If the CSV lacks required columns.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Pump curve CSV not found: {p}")

    points: list[PumpCurvePoint] = []
    with p.open("r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "flow_gpm" not in reader.fieldnames \
                or "head_ft" not in reader.fieldnames:
            raise ValueError(
                f"CSV {p} must have 'flow_gpm' and 'head_ft' columns. "
                f"Got: {reader.fieldnames}"
            )
        for row in reader:
            try:
                flow = float(row["flow_gpm"])
                head = float(row["head_ft"])
            except (KeyError, ValueError) as e:
                raise ValueError(f"Bad row in {p}: {row}") from e
            eff_str = row.get("efficiency_pct", "").strip()
            npshr_str = row.get("npshr_ft", "").strip()
            eff = float(eff_str) if eff_str else None
            npshr = float(npshr_str) if npshr_str else None
            points.append(PumpCurvePoint(flow, head, eff, npshr))

    return PumpCurve(
        manufacturer=manufacturer or p.stem.split("_")[0].title(),
        model=model or p.stem,
        impeller_code=impeller_code,
        speed_rpm=speed_rpm,
        is_placeholder=is_placeholder,
        points=points,
    )


# --- Bundled catalog --------------------------------------------------------


_BUNDLED_CURVES_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "pump_curves"
)


def load_bundled_catalog() -> dict[str, PumpCurve]:
    """Load all bundled placeholder pump curves.

    Returns a dict mapping the file stem (e.g. 'flygt_ns3127_PLACEHOLDER')
    to a PumpCurve with is_placeholder=True.
    """
    catalog: dict[str, PumpCurve] = {}
    if not _BUNDLED_CURVES_DIR.exists():
        return catalog
    for csv_path in sorted(_BUNDLED_CURVES_DIR.glob("*.csv")):
        curve = load_curve_from_csv(
            csv_path,
            manufacturer="Flygt",
            model=csv_path.stem.replace("_PLACEHOLDER", ""),
            is_placeholder="PLACEHOLDER" in csv_path.stem,
        )
        catalog[csv_path.stem] = curve
    return catalog
