#!/usr/bin/env python3
"""
Entry point for the Specs Wizard.

Usage:
    python run_wizard.py
    python run_wizard.py --output path/to/output.docx
"""

import sys
import os

# Ensure the repo root is on sys.path so `specs_wizard` resolves correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from specs_wizard.cli import main

if __name__ == "__main__":
    main()
