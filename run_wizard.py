#!/usr/bin/env python3
"""
Convenience entry point for the Specs Wizard.

Equivalent to:  python main.py specs-wizard [--output FILE]

Kept for users who prefer the explicit name; all logic lives in
specs_wizard/ and is also reachable via the unified main.py CLI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Re-use the unified entry point — inject the subcommand if not already present
_SUBCMD = "specs-wizard"
if len(sys.argv) < 2 or sys.argv[1] != _SUBCMD:
    sys.argv.insert(1, _SUBCMD)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
