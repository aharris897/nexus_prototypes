#!/usr/bin/env python3
"""
parse_input_doc.py

Converts an input .docx (or markdown-like text export) into the normalized
content JSON schema consumed by _generate_docx.js.

Usage:
    python parse_input_doc.py --input <file.docx|file.txt|file.md> --output content.json

Output JSON schema:
    { "blocks": [ { "type": "...", "text": "..." }, ... ] }

Block types mapped from input patterns:
    ##### **BOLD TEXT**          → section_title
    **PART N – ...**             → part_header  (or not_used if "(NOT USED)")
    ###### ALL CAPS              → subsection
    - text                       → bullet
    \t- text                     → bullet_indent
    END OF SECTION               → end_of_section
    (empty line)                 → spacer
    anything else                → body
"""

import sys
import re
import json
import argparse
import subprocess
import os
import tempfile

# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS (order matters – first match wins)
# ─────────────────────────────────────────────────────────────────────────────

PATTERNS = [
    # Section title: ##### **...**
    (re.compile(r'^#{5}\s+\*\*(.+?)\*\*$'), 'section_title'),

    # Part header with (NOT USED): **PART N ...(NOT USED)**
    (re.compile(r'^\*\*PART\s+\d+\s*[–\-]\s*.+?\(NOT USED\)\s*\*\*$', re.I), 'not_used'),

    # Part header: **PART N – ...**
    (re.compile(r'^\*\*PART\s+\d+\s*[–\-]\s*.+\*\*$', re.I), 'part_header'),

    # Sub-section heading: ###### TEXT (indented or not)
    (re.compile(r'^\t?#{6}\s+(.+)$'), 'subsection'),

    # End of section
    (re.compile(r'^#+\s*\*\*END\s+OF\s+SECTION\*\*$', re.I), 'end_of_section'),
    (re.compile(r'^END\s+OF\s+SECTION$', re.I), 'end_of_section'),

    # Indented bullet: \t- text
    (re.compile(r'^\t\-\s+(.+)$'), 'bullet_indent'),

    # Bullet: - text
    (re.compile(r'^\-\s+(.+)$'), 'bullet'),
]

NOT_USED_RE = re.compile(r'\(NOT\s+USED\)', re.I)


def clean_markdown_bold(text):
    """Remove markdown bold markers: **text** → text, **** text **** → text"""
    # Remove leading/trailing bold markers with spaces (artifact of some exports)
    text = re.sub(r'\*\*\s*\*\*', '', text)
    # Remove surrounding ** bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Clean up repeated spaces (e.g. "SECTION**** ****01" → "SECTION 01")
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def detect_and_clean(raw_line):
    """
    Returns (block_type, clean_text) for a given raw line.
    """
    line = raw_line.rstrip('\n')

    # Empty or whitespace-only lines → spacer
    if not line.strip():
        return ('spacer', '')

    # End of section (check before other patterns)
    if re.match(r'^#+\s*\*\*END\s*\*{0,4}\s*OF\s*\*{0,4}\s*SECTION\*\*', line, re.I):
        return ('end_of_section', 'END OF SECTION')
    if re.match(r'^END\s+OF\s+SECTION$', line.strip(), re.I):
        return ('end_of_section', 'END OF SECTION')

    # Section title (H5 with bold)
    m = re.match(r'^#{5}\s+(.+)$', line)
    if m:
        return ('section_title', clean_markdown_bold(m.group(1)))

    # Part headers (H5 or bold, containing "PART N")
    m = re.match(r'^#{1,5}\s+\*\*(.+)\*\*$', line)
    if m:
        inner = clean_markdown_bold(m.group(1))
        if re.match(r'^PART\s+\d+', inner, re.I):
            if NOT_USED_RE.search(inner):
                return ('not_used', inner)
            return ('part_header', inner)

    # **PART N – ...**  without heading marker
    m = re.match(r'^\*\*(PART\s+\d+.+)\*\*$', line)
    if m:
        inner = clean_markdown_bold(m.group(1))
        if NOT_USED_RE.search(inner):
            return ('not_used', inner)
        return ('part_header', inner)

    # Sub-section heading (H6)
    m = re.match(r'^\t?#{6}\s+(.+)$', line)
    if m:
        return ('subsection', clean_markdown_bold(m.group(1)))

    # Indented bullet
    m = re.match(r'^\t\-\s+(.+)$', line)
    if m:
        return ('bullet_indent', clean_markdown_bold(m.group(1)))

    # Regular bullet
    m = re.match(r'^\-\s+(.+)$', line)
    if m:
        return ('bullet', clean_markdown_bold(m.group(1)))

    # Default: body paragraph
    return ('body', clean_markdown_bold(line))


def parse_markdown_text(text_content):
    """Parse markdown-like text export into block list."""
    blocks = []
    prev_type = None

    for raw_line in text_content.splitlines():
        block_type, clean_text = detect_and_clean(raw_line)

        # Collapse consecutive spacers
        if block_type == 'spacer' and prev_type == 'spacer':
            continue
        # Skip spacer immediately after a heading (headings carry their own spacing)
        if block_type == 'spacer' and prev_type in ('section_title', 'part_header', 'not_used', 'subsection'):
            prev_type = block_type
            continue

        blocks.append({'type': block_type, 'text': clean_text})
        prev_type = block_type

    return blocks


def extract_docx_to_markdown(docx_path):
    """Use pandoc to convert .docx → markdown text."""
    result = subprocess.run(
        ['pandoc', '--track-changes=all', docx_path, '-t', 'markdown'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed: {result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description='Parse input doc to content JSON')
    parser.add_argument('--input',  required=True, help='Input .docx, .md, or .txt file')
    parser.add_argument('--output', required=True, help='Output content.json path')
    args = parser.parse_args()

    input_path = args.input
    ext = os.path.splitext(input_path)[1].lower()

    if ext == '.docx':
        print(f'[parse] Converting {input_path} via pandoc...')
        text_content = extract_docx_to_markdown(input_path)
    elif ext in ('.md', '.txt', '.markdown'):
        with open(input_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    else:
        print(f'[WARN] Unknown extension "{ext}" — treating as plain text')
        with open(input_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

    blocks = parse_markdown_text(text_content)
    output = {'source': os.path.basename(input_path), 'blocks': blocks}

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'[parse] Written {len(blocks)} blocks → {args.output}')


if __name__ == '__main__':
    main()
