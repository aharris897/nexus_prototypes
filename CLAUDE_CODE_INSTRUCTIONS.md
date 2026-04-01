# DOCX Style Formatter — Claude Code Instructions

## Project Overview

This toolkit analyzes a reference construction specification document
(`001_01_11_00 – Summary of Work`) and applies its exact visual style to any
number of differently-formatted input documents.

**Reference document style profile is sourced from:**
> Lift Station No. 16 Rehabilitation Project — Section 01 11 00

---

## File Structure

```
docx_formatter/
├── analyze_and_reformat.js   ← QA/QC analyzer + style profile (STYLE_PROFILE object)
├── _generate_docx.js         ← Applies style profile → writes .docx output
├── parse_input_doc.py        ← Converts any input format to normalized content JSON
├── run_pipeline.py           ← End-to-end pipeline runner (recommended entry point)
└── CLAUDE_CODE_INSTRUCTIONS.md  ← This file
```

---

## Setup (one-time)

```bash
# Install system dependencies
sudo apt install pandoc

# Install Node.js docx package
npm install -g docx

# Verify
pandoc --version
node -e "require('docx'); console.log('docx OK')"
```

---

## Usage

### Single file — QA/QC report only (no output generated)
```bash
python run_pipeline.py --input "002_01_00_00_Price_and_Payment.docx" --report-only
```

### Single file — full reformat
```bash
python run_pipeline.py \
  --input  "002_01_00_00_Price_and_Payment.docx" \
  --output "002_01_00_00_reformatted.docx"
```

### Batch — reformat an entire folder
```bash
python run_pipeline.py \
  --batch  ./input_specs/ \
  --outdir ./output_specs/
```

---

## What Claude Code Should Do

When you run this project in Claude Code, give it these instructions:

---

### INSTRUCTION SET FOR CLAUDE CODE

```
You are a document formatting assistant for a construction specification project.

Your task:
1. Accept a reference .docx file (001_01_11_00_-_Summary_of_Work.docx) as the style master
2. Accept one or more input .docx files that need to be reformatted
3. For each input file:
   a. Parse it to identify the document structure (section titles, part headers,
      sub-section headings, body paragraphs, bullets, etc.)
   b. Run a QA/QC comparison against the reference style profile defined in
      analyze_and_reformat.js (STYLE_PROFILE object)
   c. Report any deviations: page size, font, heading sizes, spacing, bullet style
   d. Reformat the document using _generate_docx.js preserving ALL TEXT content
      while applying the correct visual style

Files to work with are in the current directory.
Use run_pipeline.py as the main entry point.

Important rules:
- NEVER change any substantive text content — only formatting/style
- CONTRACTOR, OWNER, ENGINEER should remain ALL CAPS in body text
- Section numbers follow CSI MasterFormat (e.g., "01 11 00")
- Every section must end with "END OF SECTION"
- PART 2 – PRODUCTS and PART 3 – EXECUTION should have "(NOT USED)" if empty
- Page layout: US Letter, 1.25" left margin, 1" all other margins
- Font: Arial throughout
- Headers and footers must be present (project name in header, page number in footer)
```

---

## Style Profile Reference (from 001_01_11_00)

| Element | Style | Font | Size | Bold | Caps |
|---|---|---|---|---|---|
| Section Title | H1 | Arial | 14pt | ✅ | ALL CAPS |
| Part Header | H2 | Arial | 12pt | ✅ | Mixed |
| Sub-Section | H3 | Arial | 11pt | ✅ | ALL CAPS |
| Body Text | Normal | Arial | 10pt | ❌ | — |
| Bullet L1 | List Bullet | Arial | 10pt | ❌ | — |
| Bullet L2 | List Bullet 2 | Arial | 10pt | ❌ | — |
| Footer | — | Arial | 9pt | ❌ | — |

### Page Layout
- **Size:** US Letter (8.5" × 11")
- **Margins:** Top 1" / Bottom 1" / Left 1.25" / Right 1"
- **Header:** Project name + horizontal rule
- **Footer:** Page number (left) + Owner name (right)

### Spacing (in DXA twips, 1440 = 1 inch)
| Element | Before | After |
|---|---|---|
| Section Title | 240 | 120 |
| Part Header | 200 | 120 |
| Sub-Section | 160 | 60 |
| Body | 0 | 120 |
| Bullet | 0 | 60 |

---

## QA/QC Issue Severity Levels

| Severity | Color | Meaning |
|---|---|---|
| HIGH 🔴 | Red | Must fix — visible formatting error (wrong page size, missing font, unicode bullets) |
| MEDIUM 🟡 | Yellow | Should fix — deviation from reference but not critical |
| LOW 🔵 | Blue | Minor — structural note (missing END OF SECTION, etc.) |

---

## Troubleshooting

**"pandoc not found"**
```bash
sudo apt-get install -y pandoc
```

**"Cannot find module 'docx'"**
```bash
npm install -g docx
# or locally:
npm install docx
```

**Output docx fails to open in Word**
```bash
python /mnt/skills/public/docx/scripts/office/validate.py output.docx
```

**Input file has unusual formatting not recognized**
- Open `parse_input_doc.py` and add a new regex pattern in the `PATTERNS` list
- Test with: `python parse_input_doc.py --input myfile.txt --output test.json && cat test.json`

---

## Adding New Input Documents

1. Place the `.docx` file in `./input_specs/`
2. Run: `python run_pipeline.py --batch ./input_specs/ --outdir ./output_specs/`
3. Review QA/QC report printed to console
4. Inspect output files in `./output_specs/`

If text content needs manual review first:
```bash
python run_pipeline.py --input myspec.docx --report-only
```

---

## Extending the Style Profile

All style values live in the `STYLE_PROFILE` constant at the top of
`analyze_and_reformat.js` and are mirrored in `_generate_docx.js` as `PROFILE`.

To update (e.g. change font from Arial to Calibri):
1. Edit `STYLE_PROFILE.fonts.default` in `analyze_and_reformat.js`
2. Edit `PROFILE.font` in `_generate_docx.js`
3. Re-run the pipeline

---

*Generated for: Lift Station No. 16 Rehabilitation Project*
*City of Riviera Beach Utility Special District*
