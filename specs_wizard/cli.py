"""
CLI entry point for the Specs Wizard.

Usage:
    python run_wizard.py [--output my_spec.docx]
"""

import argparse
import sys

from .wizard import collect_spec
from .generator import build_docx


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="specs-wizard",
        description=(
            "Interactive wizard for creating CSI MasterFormat "
            "construction specification sections."
        ),
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output .docx path (overrides the wizard prompt).",
        default=None,
    )
    args = parser.parse_args(argv)

    try:
        spec = collect_spec()
    except KeyboardInterrupt:
        print("\n\n  Wizard cancelled.")
        sys.exit(0)

    output_path = args.output or spec.output_path

    try:
        saved = build_docx(spec, output_path)
        print(f"  Specification saved → {saved}")
    except ImportError as exc:
        print(
            f"\n  ERROR: Missing dependency — {exc}\n"
            "  Run:  pip install python-docx\n"
        )
        sys.exit(1)
    except Exception as exc:
        print(f"\n  ERROR generating DOCX: {exc}")
        sys.exit(1)
