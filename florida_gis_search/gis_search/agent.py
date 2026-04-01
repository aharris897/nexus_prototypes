"""
Claude-powered GIS data search agent.

Uses claude-opus-4-6 with the web_search and web_fetch server-side tools to
locate publicly available GIS datasets for Florida counties, then parses the
findings into structured GISDataset objects via structured output.
"""

import json
import os
import sys
import time
from typing import Callable

import anthropic

from .models import GISDataset

# ── Model & tool configuration ────────────────────────────────────────────────

MODEL = "claude-opus-4-6"

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]

# ── JSON schema for structured dataset output ──────────────────────────────────

DATASET_SCHEMA = {
    "type": "object",
    "properties": {
        "datasets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":            {"type": "string"},
                    "county":          {"type": "string"},
                    "category":        {"type": "string"},
                    "description":     {"type": "string"},
                    "url":             {"type": "string"},
                    "format":          {"type": "string"},
                    "direct_download": {"type": "boolean"},
                    "source":          {"type": "string"},
                },
                "required": [
                    "name", "county", "category", "description",
                    "url", "format", "direct_download", "source",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["datasets"],
    "additionalProperties": False,
}

# ── System prompts ─────────────────────────────────────────────────────────────

SEARCH_SYSTEM_PROMPT = """\
You are a GIS data researcher specializing in Florida county geographic data.
Your task is to find publicly available GIS datasets for a specified Florida county.

Focus on these data types (in priority order):
1. PARCELS — property parcel/tax parcel polygons (county property appraiser, county GIS portal)
2. BOUNDARIES — county boundaries, municipal/city limits, jurisdiction boundaries,
   commission districts, flood zones, special districts
3. WATER — potable water distribution/transmission mains, water service areas,
   water plant locations
4. WASTEWATER — sewer/wastewater collection mains, wastewater service areas,
   lift stations, force mains
5. RECLAIMED WATER — reclaimed/reuse water distribution lines, reclaimed water
   service areas, reuse facilities

Also collect any other notable utility or infrastructure GIS layers you encounter.

Key sources to search:
• The county's official GIS portal or ArcGIS Hub open data site
• County Property Appraiser website (for parcel data)
• ArcGIS Hub — search hub.arcgis.com for "[County] county florida"
• Florida Geographic Data Library (fgdl.org) — statewide datasets
• Florida DEP GIS data (floridadep.gov/gis)
• Water management districts:
  - SFWMD (South Florida) — sfwmd.gov
  - SWFWMD (Southwest Florida) — swfwmd.state.fl.us
  - SJRWMD (St. Johns River) — sjrwmd.com
  - SRWMD (Suwannee River) — srwmd.org
  - NWFWMD (Northwest Florida) — nwfwmd.state.fl.us
• The county's utility authority or water/wastewater department website
• City/municipality GIS portals within the county (especially the county seat)

For every dataset found, record:
• Exact dataset name
• Category (parcels / boundaries / water / wastewater / reclaimed_water / utilities / other)
• A one-sentence description
• The most direct URL available (prefer direct .zip / .geojson / .gdb download links)
• File format (shapefile / geojson / gdb / kmz / csv / rest_api / wfs / unknown)
• Whether the URL is a direct file download (true) or a portal/landing page (false)
• The name of the data source / organization

Be thorough — search multiple sources and look for real, working download URLs.\
"""

PARSE_SYSTEM_PROMPT = """\
You are a data extraction assistant. Given research notes about GIS datasets found
for a Florida county, extract each dataset into a structured JSON list.

Rules:
- category must be one of: parcels, boundaries, water, wastewater, reclaimed_water, utilities, other
- format must be one of: shapefile, geojson, gdb, kmz, csv, rest_api, wfs, unknown
- direct_download is true only if the url points directly to a downloadable file
  (ends in .zip, .geojson, .json, .kml, .kmz, .csv, etc.)
- Deduplicate — do not include the same dataset twice
- county should be just the county name with no "County" suffix
- If you are uncertain about a field, make a reasonable best-guess

Output ONLY valid JSON matching this structure (no markdown, no extra text):
{
  "datasets": [
    {
      "name": "...",
      "county": "...",
      "category": "...",
      "description": "...",
      "url": "...",
      "format": "...",
      "direct_download": true|false,
      "source": "..."
    }
  ]
}\
"""


# ── Agent class ────────────────────────────────────────────────────────────────

class GISSearchAgent:
    """
    Two-phase agent:
      Phase 1 — Claude uses web_search + web_fetch to gather GIS data information.
      Phase 2 — Claude parses the free-form findings into structured JSON.
    """

    def __init__(
        self,
        api_key: str | None = None,
        on_status: Callable[[str], None] | None = None,
    ):
        """
        Args:
            api_key:   Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
            on_status: Optional callback for status/progress messages.
        """
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self._status = on_status or (lambda msg: None)

    # ── Public API ─────────────────────────────────────────────────────────────

    def search(self, county: str) -> list[GISDataset]:
        """
        Search for GIS datasets for a Florida county.

        Returns a list of GISDataset objects (may be empty if nothing found).
        """
        self._status(f"Searching for GIS data in {county} County, Florida…")

        # Phase 1: web search
        raw_findings = self._web_search_phase(county)

        if not raw_findings.strip():
            self._status("  No findings returned from web search.")
            return []

        # Phase 2: parse to structured JSON
        self._status("  Parsing results into structured dataset list…")
        datasets = self._parse_phase(county, raw_findings)

        self._status(f"  Found {len(datasets)} dataset(s) for {county} County.")
        return datasets

    # ── Phase 1: web search ────────────────────────────────────────────────────

    def _web_search_phase(self, county: str) -> str:
        """
        Ask Claude to search the web for GIS data for the given county.
        Uses server-side web_search + web_fetch tools; handles pause_turn.
        Returns Claude's free-form research summary as a string.
        """
        user_prompt = (
            f"Find all publicly available GIS datasets for {county} County, Florida. "
            "Focus on: parcel data, county/municipal boundaries, potable water infrastructure, "
            "wastewater/sewer infrastructure, and reclaimed/reuse water infrastructure. "
            "Search the county GIS portal, property appraiser site, ArcGIS Hub, FGDL, "
            "and any relevant water management district or utility websites. "
            "List every dataset you find with its name, category, description, URL, "
            "file format, and data source."
        )

        messages: list[dict] = [{"role": "user", "content": user_prompt}]
        max_continuations = 6

        for attempt in range(max_continuations):
            self._status(f"  [Search attempt {attempt + 1}/{max_continuations}]")
            response = self._create_with_retry(
                model=MODEL,
                max_tokens=8000,
                thinking={"type": "adaptive"},
                system=SEARCH_SYSTEM_PROMPT,
                tools=WEB_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                # Extract the final text block
                return self._extract_text(response)

            if response.stop_reason == "pause_turn":
                # Server-side tool loop hit iteration limit — re-send to continue
                self._status("  Continuing search (server tool limit reached)…")
                messages = [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": response.content},
                ]
                continue

            # Unexpected stop reason — return whatever text we have
            self._status(
                f"  Warning: unexpected stop_reason '{response.stop_reason}'"
            )
            return self._extract_text(response)

        self._status("  Warning: max search continuations reached.")
        return self._extract_text(response)  # type: ignore[possibly-undefined]

    # ── Phase 2: structured parsing ────────────────────────────────────────────

    def _parse_phase(self, county: str, raw_findings: str) -> list[GISDataset]:
        """
        Ask Claude to convert the free-form research notes into structured JSON
        using structured output (output_config.format = json_schema).
        """
        user_prompt = (
            f"Here are the GIS datasets found for {county} County, Florida:\n\n"
            f"{raw_findings}\n\n"
            "Extract each dataset into the required JSON structure."
        )

        response = self._create_with_retry(
            model=MODEL,
            max_tokens=4000,
            system=PARSE_SYSTEM_PROMPT,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": DATASET_SCHEMA,
                }
            },
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_json = self._extract_text(response)

        try:
            data = json.loads(raw_json)
            return [GISDataset(**item) for item in data.get("datasets", [])]
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            self._status(f"  Warning: failed to parse structured output — {exc}")
            return []

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _create_with_retry(self, **kwargs) -> anthropic.types.Message:
        """Call client.messages.create with exponential backoff on rate limits."""
        delays = [2, 4, 8, 16]
        last_exc: Exception | None = None

        for i, delay in enumerate([0] + delays):
            if delay:
                self._status(f"  Rate limited — retrying in {delay}s…")
                time.sleep(delay)
            try:
                return self.client.messages.create(**kwargs)
            except anthropic.RateLimitError as exc:
                last_exc = exc
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                else:
                    raise

        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Return the concatenated text from all TextBlock content blocks."""
        parts = [
            block.text
            for block in response.content
            if hasattr(block, "text") and block.type == "text"
        ]
        return "\n".join(parts).strip()
