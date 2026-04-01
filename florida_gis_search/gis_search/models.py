"""Data models for GIS dataset search results."""

from dataclasses import dataclass, field
from typing import Optional


# Human-readable category labels
CATEGORY_LABELS: dict[str, str] = {
    "parcels": "Parcels",
    "boundaries": "Boundaries",
    "water": "Water Utilities",
    "wastewater": "Wastewater Utilities",
    "reclaimed_water": "Reclaimed Water",
    "utilities": "Utilities (General)",
    "other": "Other",
}

# Priority order for display (most relevant first)
CATEGORY_ORDER = [
    "parcels",
    "boundaries",
    "water",
    "wastewater",
    "reclaimed_water",
    "utilities",
    "other",
]

FORMAT_LABELS: dict[str, str] = {
    "shapefile": "Shapefile (.zip)",
    "geojson": "GeoJSON",
    "gdb": "File Geodatabase",
    "kmz": "KMZ/KML",
    "csv": "CSV",
    "rest_api": "ArcGIS REST API",
    "wfs": "WFS Service",
    "unknown": "Unknown",
}


@dataclass
class GISDataset:
    """Represents a single GIS dataset found for a county."""

    name: str
    county: str
    category: str  # parcels | boundaries | water | wastewater | reclaimed_water | utilities | other
    description: str
    url: str
    format: str    # shapefile | geojson | gdb | kmz | csv | rest_api | wfs | unknown
    direct_download: bool
    source: str

    # Populated after download
    local_path: Optional[str] = field(default=None, compare=False)

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.replace("_", " ").title())

    @property
    def format_label(self) -> str:
        return FORMAT_LABELS.get(self.format, self.format.upper())

    @property
    def display_name(self) -> str:
        """Short display name for list menus."""
        return f"[{self.category_label}] {self.name} ({self.format_label}) — {self.source}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "county": self.county,
            "category": self.category,
            "description": self.description,
            "url": self.url,
            "format": self.format,
            "direct_download": self.direct_download,
            "source": self.source,
        }
