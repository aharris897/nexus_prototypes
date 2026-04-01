"""
Dataset downloader.

Handles:
  • Direct HTTP file downloads (ZIP, GeoJSON, CSV, KMZ, …)
  • ArcGIS REST FeatureServer/MapServer exports (constructs query URLs)
  • WFS GetFeature requests
  • Non-downloadable URLs (portal pages) — prints link for manual retrieval
"""

import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Callable

import requests
from tqdm import tqdm

from .models import GISDataset

# ── Constants ──────────────────────────────────────────────────────────────────

DOWNLOAD_TIMEOUT = 120          # seconds per request
CHUNK_SIZE = 1024 * 64          # 64 KiB chunks

# Patterns that indicate an ArcGIS REST service endpoint
_ARCGIS_REST_RE = re.compile(
    r"(https?://.+/rest/services/.+/(Feature|Map)Server/\d+)",
    re.IGNORECASE,
)

# File extensions that signal a direct downloadable file
_DIRECT_EXTENSIONS = {
    ".zip", ".geojson", ".json", ".kml", ".kmz", ".csv", ".gdb",
    ".shp", ".gpkg", ".sqlite",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GISDataSearchTool/0.1; "
        "+https://github.com/nexus_prototypes)"
    )
}


# ── Public helper ──────────────────────────────────────────────────────────────

def download_datasets(
    datasets: list[GISDataset],
    output_dir: str = "./gis_downloads",
    on_status: Callable[[str], None] | None = None,
) -> list[GISDataset]:
    """
    Download a list of datasets to *output_dir*.

    Updates each dataset's ``local_path`` field on success.
    Returns the same list (mutated in place) for chaining.
    """
    status = on_status or print
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for dataset in datasets:
        county_dir = out / _safe_name(dataset.county)
        county_dir.mkdir(exist_ok=True)

        status(f"\n→ {dataset.name}  [{dataset.category_label}]")
        status(f"  Source : {dataset.source}")
        status(f"  URL    : {dataset.url}")

        try:
            local_path = _download_one(dataset, county_dir, status)
            dataset.local_path = str(local_path)
            status(f"  ✓ Saved to {local_path}")
        except SkipDownload as exc:
            status(f"  ⚠  {exc}")
        except Exception as exc:  # noqa: BLE001
            status(f"  ✗ Download failed: {exc}")

    return datasets


# ── Internal logic ─────────────────────────────────────────────────────────────

class SkipDownload(Exception):
    """Raised when a dataset cannot/should not be auto-downloaded."""


def _download_one(
    dataset: GISDataset,
    dest_dir: Path,
    status: Callable[[str], None],
) -> Path:
    """Download a single dataset; return the local file path."""
    url = dataset.url.strip()

    # 1. ArcGIS REST FeatureServer/MapServer — build an export URL
    arcgis_match = _ARCGIS_REST_RE.match(url)
    if arcgis_match or dataset.format == "rest_api":
        return _download_arcgis_rest(dataset, url, dest_dir, status)

    # 2. WFS service
    if dataset.format == "wfs" or "wfs" in url.lower():
        return _download_wfs(dataset, url, dest_dir, status)

    # 3. Direct or plausible direct-download URL
    parsed = urllib.parse.urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if dataset.direct_download or ext in _DIRECT_EXTENSIONS:
        return _download_direct(dataset, url, dest_dir, status)

    # 4. Everything else — try a HEAD request first to check content-type
    try:
        head = requests.head(url, headers=HEADERS, timeout=30, allow_redirects=True)
        ct = head.headers.get("content-type", "")
        if any(
            sig in ct
            for sig in ("octet-stream", "zip", "json", "kml", "csv", "gdb", "geo")
        ):
            return _download_direct(dataset, url, dest_dir, status)
    except requests.RequestException:
        pass

    raise SkipDownload(
        f"URL appears to be a portal page (not directly downloadable).\n"
        f"  Please visit manually: {url}"
    )


def _download_direct(
    dataset: GISDataset,
    url: str,
    dest_dir: Path,
    status: Callable[[str], None],
) -> Path:
    """Stream-download a file with a tqdm progress bar."""
    response = requests.get(
        url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True
    )
    response.raise_for_status()

    # Determine filename
    filename = _filename_from_response(response, url, dataset)
    dest = dest_dir / filename

    # Avoid re-downloading identical file
    if dest.exists():
        existing_size = dest.stat().st_size
        total = int(response.headers.get("content-length", 0))
        if total and existing_size == total:
            status(f"  Already downloaded — skipping.")
            return dest

    total = int(response.headers.get("content-length", 0))
    with (
        open(dest, "wb") as fh,
        tqdm(
            total=total or None,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=f"  {filename[:40]}",
            leave=False,
        ) as bar,
    ):
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                fh.write(chunk)
                bar.update(len(chunk))

    return dest


def _download_arcgis_rest(
    dataset: GISDataset,
    url: str,
    dest_dir: Path,
    status: Callable[[str], None],
) -> Path:
    """
    Export an ArcGIS FeatureServer/MapServer layer as GeoJSON.

    Constructs a /query endpoint URL and streams the response.
    """
    # Strip any trailing query string from the service base URL
    base = _ARCGIS_REST_RE.match(url)
    service_url = base.group(1) if base else url.split("?")[0].rstrip("/")

    export_url = (
        f"{service_url}/query"
        "?where=1%3D1"
        "&outFields=*"
        "&f=geojson"
        "&returnGeometry=true"
    )

    status(f"  Exporting ArcGIS layer → {export_url}")

    filename = _safe_name(dataset.name) + ".geojson"
    dest = dest_dir / filename

    response = requests.get(
        export_url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True
    )
    response.raise_for_status()

    content = response.content
    # Validate it's actually GeoJSON (not an ArcGIS error page)
    if b'"features"' not in content[:2048]:
        raise SkipDownload(
            f"ArcGIS export did not return valid GeoJSON. "
            f"Visit the service page manually: {url}"
        )

    dest.write_bytes(content)
    return dest


def _download_wfs(
    dataset: GISDataset,
    url: str,
    dest_dir: Path,
    status: Callable[[str], None],
) -> Path:
    """Construct a WFS GetFeature request and download as GeoJSON."""
    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    # Build a minimal GetFeature request if not already one
    if "request" not in {k.lower() for k in params}:
        type_name = params.get("typeName") or params.get("TYPENAME") or dataset.name
        wfs_params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
        }
        base_url = urllib.parse.urlunparse(parsed._replace(query=""))
        export_url = f"{base_url}?" + urllib.parse.urlencode(wfs_params)
    else:
        export_url = url

    status(f"  WFS GetFeature → {export_url}")

    filename = _safe_name(dataset.name) + ".geojson"
    dest = dest_dir / filename

    response = requests.get(
        export_url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True
    )
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


# ── Filename helpers ───────────────────────────────────────────────────────────

def _filename_from_response(
    response: requests.Response,
    url: str,
    dataset: GISDataset,
) -> str:
    """Derive a safe local filename from response headers or the URL."""
    # Try Content-Disposition header
    cd = response.headers.get("content-disposition", "")
    if "filename=" in cd:
        fname = cd.split("filename=")[-1].strip().strip('"').strip("'")
        if fname:
            return _safe_name(fname)

    # Fall back to URL path
    parsed = urllib.parse.urlparse(url)
    path_name = Path(parsed.path).name
    if path_name and "." in path_name:
        return _safe_name(path_name)

    # Build from dataset metadata
    ext_map = {
        "shapefile":  ".zip",
        "geojson":    ".geojson",
        "gdb":        ".gdb.zip",
        "kmz":        ".kmz",
        "kml":        ".kml",
        "csv":        ".csv",
        "rest_api":   ".geojson",
        "wfs":        ".geojson",
    }
    ext = ext_map.get(dataset.format, ".download")
    return _safe_name(f"{dataset.county}_{dataset.name}") + ext


def _safe_name(name: str) -> str:
    """Return a filesystem-safe version of a name."""
    name = name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    name = re.sub(r"[^\w.\-]", "", name)
    return name[:120]  # cap length
