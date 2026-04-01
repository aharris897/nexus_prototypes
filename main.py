#!/usr/bin/env python3
"""
Nexus Prototypes — unified CLI entry point
==========================================

Available tools
---------------
  gis-search     Search for and download Florida county GIS data using Claude AI.
  specs-wizard   Interactive CSI MasterFormat construction specification builder.

Usage
-----
  # GIS search (subcommand explicit)
  python main.py gis-search
  python main.py gis-search --counties Orange
  python main.py gis-search --counties "Orange,Hillsborough" --no-download
  python main.py gis-search --counties Orange --output-dir ./my_gis_data

  # Specs wizard
  python main.py specs-wizard
  python main.py specs-wizard --output my_spec.docx

  # Legacy: no subcommand defaults to gis-search (backward-compatible)
  python main.py --counties Orange
"""

import argparse
import sys


# ── Sub-parser factories ──────────────────────────────────────────────────────

def _add_gis_search_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "gis-search",
        help="Search for and download Florida county GIS datasets (Claude AI).",
        description=(
            "Uses Claude AI to discover publicly available GIS datasets for "
            "Florida counties: parcels, boundaries, water/wastewater/reclaimed."
        ),
    )
    p.add_argument(
        "--counties",
        metavar="COUNTY[,COUNTY…]",
        type=str,
        help=(
            "Comma-separated Florida county name(s) to search. "
            "If omitted, an interactive county picker is shown."
        ),
    )
    p.add_argument(
        "--output-dir",
        metavar="DIR",
        type=str,
        default="./gis_downloads",
        help="Directory to save downloaded files (default: ./gis_downloads).",
    )
    p.add_argument(
        "--no-download",
        action="store_true",
        help="List found datasets without downloading any files.",
    )


def _add_specs_wizard_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "specs-wizard",
        help="Interactive CSI MasterFormat construction specification builder.",
        description=(
            "Step-by-step wizard that collects project and section details, "
            "then generates a properly styled .docx specification document."
        ),
    )
    p.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output .docx file path (overrides the wizard prompt).",
        default=None,
    )


# ── Dispatch ──────────────────────────────────────────────────────────────────

def _run_gis_search(args) -> None:
    try:
        from gis_search.cli import run_cli
    except ImportError as exc:
        print(
            f"ERROR: Missing dependency — {exc}\n"
            "Run:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    counties: list[str] | None = None
    if args.counties:
        counties = [c.strip() for c in args.counties.split(",") if c.strip()]

    run_cli(
        counties=counties,
        output_dir=args.output_dir,
        no_download=args.no_download,
    )


def _run_specs_wizard(args) -> None:
    try:
        from specs_wizard.wizard import collect_spec
        from specs_wizard.generator import build_docx
    except ImportError as exc:
        print(
            f"ERROR: Missing dependency — {exc}\n"
            "Run:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        spec = collect_spec()
    except KeyboardInterrupt:
        print("\n\n  Wizard cancelled.")
        sys.exit(0)

    output_path = args.output or spec.output_path

    try:
        saved = build_docx(spec, output_path)
        print(f"  Specification saved → {saved}")
    except Exception as exc:
        print(f"\n  ERROR generating DOCX: {exc}", file=sys.stderr)
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # ── Build top-level parser ────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        prog="nexus",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")

    subparsers = parser.add_subparsers(dest="tool", metavar="TOOL")
    _add_gis_search_parser(subparsers)
    _add_specs_wizard_parser(subparsers)

    # ── Legacy top-level GIS flags (no subcommand given) ─────────────────────
    # These are kept for backward compatibility: `python main.py --counties …`
    parser.add_argument(
        "--counties",
        metavar="COUNTY[,COUNTY…]",
        type=str,
        help=argparse.SUPPRESS,   # hidden — use gis-search subcommand instead
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        type=str,
        default="./gis_downloads",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    # Default to gis-search when called with legacy flags (no subcommand)
    if args.tool is None:
        args.tool = "gis-search"

    if args.tool == "gis-search":
        _run_gis_search(args)
    elif args.tool == "specs-wizard":
        _run_specs_wizard(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
