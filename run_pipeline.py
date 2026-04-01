#!/usr/bin/env python3
"""
run_pipeline.py  –  End-to-end document reformatter pipeline

Takes any input .docx (or .txt/.md export) and produces a fully
styled .docx matching the 001_01_11_00 reference style profile.

Usage:
    python run_pipeline.py --input <file.docx> [--output <out.docx>]
    python run_pipeline.py --batch <folder/> [--outdir <output/>]
    python run_pipeline.py --input <file.docx> --report-only

Pipeline steps:
    1. parse_input_doc.py   → content.json
    2. analyze_and_reformat.js  → QA/QC report
    3. _generate_docx.js    → styled output.docx
    4. validate.py          → validation check
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = '/mnt/skills/public/docx/scripts/office'


def run(cmd, label=''):
    """Run a shell command and stream output."""
    print(f'\n>>> {label or cmd}')
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0:
        print(f'[ERROR] Step failed (exit {result.returncode})')
    return result.returncode == 0


def process_file(input_path, output_path, report_only=False):
    """Full pipeline for a single file."""
    print('\n' + '─' * 60)
    print(f'Processing: {os.path.basename(input_path)}')
    print('─' * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        content_json = os.path.join(tmpdir, 'content.json')

        # ── Step 1: Parse input to normalized content JSON ───────────────────
        ok = run(
            f'python {SCRIPT_DIR}/parse_input_doc.py --input "{input_path}" --output "{content_json}"',
            label='Step 1/4: Parse input document'
        )
        if not ok:
            print('[SKIP] Could not parse input — check format.')
            return False

        # ── Step 2: QA/QC analysis ────────────────────────────────────────────
        run(
            f'node {SCRIPT_DIR}/analyze_and_reformat.js --input "{input_path}" --report-only',
            label='Step 2/4: QA/QC style analysis'
        )

        if report_only:
            print('[INFO] --report-only: Skipping generation steps.')
            return True

        # ── Step 3: Generate reformatted docx ────────────────────────────────
        ok = run(
            f'node {SCRIPT_DIR}/_generate_docx.js --content "{content_json}" --output "{output_path}"',
            label='Step 3/4: Generate styled .docx'
        )
        if not ok:
            print('[SKIP] Generation failed.')
            return False

        # ── Step 4: Validate ──────────────────────────────────────────────────
        run(
            f'python {SKILLS_DIR}/validate.py "{output_path}"',
            label='Step 4/4: Validate output'
        )

    print(f'\n✅ Output: {output_path}')
    return True


def main():
    parser = argparse.ArgumentParser(description='DOCX style reformatter pipeline')
    parser.add_argument('--input',       help='Single input .docx/.txt/.md file')
    parser.add_argument('--output',      help='Output .docx path')
    parser.add_argument('--batch',       help='Folder of input files')
    parser.add_argument('--outdir',      help='Output folder for batch mode', default='./output')
    parser.add_argument('--report-only', action='store_true', help='Only print QA report')
    args = parser.parse_args()

    # ── Check dependencies ────────────────────────────────────────────────────
    missing = []
    if not shutil.which('pandoc'):
        missing.append('pandoc  (sudo apt install pandoc)')
    if not shutil.which('node'):
        missing.append('node  (https://nodejs.org)')
    if subprocess.run('node -e "require(\'docx\')"', shell=True,
                      capture_output=True).returncode != 0:
        missing.append('docx npm package  (npm install -g docx)')
    if missing:
        print('\n[SETUP] Missing dependencies:\n  ' + '\n  '.join(missing))
        print('\nRun: sudo apt install pandoc && npm install -g docx')
        sys.exit(1)

    # ── Single file ───────────────────────────────────────────────────────────
    if args.input:
        out = args.output or args.input.rsplit('.', 1)[0] + '_reformatted.docx'
        process_file(args.input, out, report_only=args.report_only)

    # ── Batch mode ────────────────────────────────────────────────────────────
    elif args.batch:
        os.makedirs(args.outdir, exist_ok=True)
        exts = {'.docx', '.txt', '.md'}
        files = [f for f in os.listdir(args.batch)
                 if os.path.splitext(f)[1].lower() in exts]
        print(f'Batch: {len(files)} file(s) in {args.batch}')

        results = []
        for f in sorted(files):
            inp = os.path.join(args.batch, f)
            out = os.path.join(args.outdir, os.path.splitext(f)[0] + '_reformatted.docx')
            ok = process_file(inp, out, report_only=args.report_only)
            results.append((f, '✅' if ok else '❌'))

        print('\n' + '═' * 50)
        print('BATCH SUMMARY')
        print('═' * 50)
        for fname, status in results:
            print(f'  {status}  {fname}')

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
