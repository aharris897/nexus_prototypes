# Specs Wizard — Instructions

Interactive CLI that guides you step-by-step through creating a
CSI MasterFormat construction specification section and outputs a
properly styled `.docx` file.

---

## Setup (one-time)

```bash
pip install -r requirements.txt   # from repo root; adds python-docx
```

---

## Usage

### Interactive wizard (recommended)

```bash
python run_wizard.py
```

The wizard walks you through six steps:

| Step | What you enter |
|------|----------------|
| 1 | Project name, number, owner, engineer, contractor |
| 2 | CSI section number (e.g., `46 00 00`) and section title |
| 3 | Part 1 – General sub-sections (select from checklist, then enter content) |
| 4 | Part 2 – Products (mark as NOT USED, or add sub-sections) |
| 5 | Part 3 – Execution (add sub-sections) |
| 6 | Output filename |

### Override output path

```bash
python run_wizard.py --output my_section.docx
```

---

## Content Entry Format

At each sub-section prompt:

```
    > Furnish and install pump station as shown on the drawings.
    > - Wet well rehabilitation including cleaning and coating.
    > - Pump and motor replacement.
    >   - Verify motor frame dimensions prior to ordering.
    >
```

| Prefix | Result |
|--------|--------|
| *(none)* | Body paragraph |
| `- text` or `• text` | Level-1 bullet |
| `  - text` (2 spaces) | Level-2 bullet |
| *(empty line)* | End input for this sub-section |

---

## Output Style Profile

Matches the reference document (`001_01_11_00 – Summary of Work`):

| Element | Font | Size | Bold | Caps |
|---------|------|------|------|------|
| Section Title | Arial | 14 pt | ✅ | ALL CAPS |
| Part Header | Arial | 12 pt | ✅ | Mixed |
| Sub-Section | Arial | 11 pt | ✅ | ALL CAPS |
| Body Text | Arial | 10 pt | ❌ | — |
| Bullet L1/L2 | Arial | 10 pt | ❌ | — |
| Footer | Arial | 9 pt | ❌ | — |

**Page layout:** US Letter, 1.25″ left margin, 1″ top/bottom/right  
**Header:** Project name with bottom border rule  
**Footer:** `Page N` (left) · Owner name (right)  
**End marker:** `END OF SECTION` centered at bottom

---

## File Structure

```
specs_wizard/
├── __init__.py      Package init
├── models.py        SpecSection, SpecPart, SubSection dataclasses
├── templates.py     CSI sub-section lists and hints
├── wizard.py        Step-by-step interactive questionnaire
├── generator.py     python-docx DOCX builder
├── cli.py           argparse entry point
└── INSTRUCTIONS.md  This file

run_wizard.py        Top-level runner (python run_wizard.py)
```

---

## Programmatic Use

```python
from specs_wizard.models import (
    SpecSection, ProjectInfo, SpecPart, SubSection,
    ContentLine, PARAGRAPH, BULLET_L1,
)
from specs_wizard.generator import build_docx

spec = SpecSection(
    project=ProjectInfo(
        project_name="Lift Station No. 16",
        project_number="2024-001",
        owner="City of Riviera Beach",
        engineer="",
        contractor="CONTRACTOR",
    ),
    csi_number="01 11 00",
    section_title="SUMMARY OF WORK",
    parts=[...],
    output_path="01_11_00_Summary_of_Work.docx",
)

path = build_docx(spec)
```

---

*Lift Station No. 16 Rehabilitation Project — City of Riviera Beach Utility Special District*
