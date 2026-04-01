#!/usr/bin/env python3
"""
Florida GIS Data Search Tool
=============================
Uses Claude AI to search for publicly available GIS datasets within
designated Florida counties, with a focus on:

  • Parcel / property boundary data
  • County & municipal boundary data
  • Water, wastewater, and reclaimed water utility infrastructure

Usage
-----
  python main.py                                  # fully interactive
  python main.py --counties Orange                # single county
  python main.py --counties "Orange,Hillsborough" # multiple counties
  python main.py --counties Orange --no-download  # list only, no download
  python main.py --counties Orange --output-dir ./my_gis_data
"""

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gis_search",
        description="Search for and download Florida county GIS data using Claude AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--counties",
        metavar="COUNTY[,COUNTY…]",
        type=str,
        help=(
            "Comma-separated Florida county name(s) to search. "
            "If omitted, an interactive county picker is shown."
        ),
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        type=str,
        default="./gis_downloads",
        help="Directory to save downloaded files (default: ./gis_downloads).",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="List found datasets without downloading any files.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Lazy import so --help / --version don't require anthropic to be installed
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


if __name__ == "__main__":
    main()
