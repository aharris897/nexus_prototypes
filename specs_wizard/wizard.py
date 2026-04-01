"""
Interactive step-by-step questionnaire for the Specs Wizard.

Collects all data needed to produce a CSI MasterFormat spec section and
returns a populated SpecSection dataclass.

Content entry rules (applies to every sub-section prompt):
  • Plain text  → body paragraph
  • Line starting with  -  or  •  → level-1 bullet
  • Line starting with two spaces then  -  or  •  → level-2 bullet
  • Empty line → end of input for that sub-section
"""

import re
import sys

try:
    import questionary
    from questionary import Choice, Separator
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False

from .models import (
    BULLET_L1, BULLET_L2, PARAGRAPH,
    ContentLine, ProjectInfo, SpecPart, SpecSection, SubSection,
)
from .templates import (
    DEFAULT_PART1_SELECTED, PART1_HINTS, PART1_SUBSECTIONS,
    COMMON_PART2_SUBSECTIONS, COMMON_PART3_SUBSECTIONS,
)


# ── ANSI helpers (same pattern as gis_search/cli.py) ─────────────────────────

def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _is_tty() else text


def bold(t: str) -> str:  return _c("1", t)
def cyan(t: str) -> str:  return _c("36", t)
def dim(t: str) -> str:   return _c("2", t)
def green(t: str) -> str: return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)


# ── Low-level input helpers ───────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    """Single-line text prompt, with questionary if available."""
    if _HAS_QUESTIONARY:
        val = questionary.text(prompt, default=default).ask()
        if val is None:
            sys.exit(0)
        return val.strip()
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {prompt}{suffix}: ").strip()
    return raw if raw else default


def _ask_confirm(prompt: str, default: bool = True) -> bool:
    if _HAS_QUESTIONARY:
        val = questionary.confirm(prompt, default=default).ask()
        if val is None:
            sys.exit(0)
        return val
    suffix = " [Y/n]" if default else " [y/N]"
    raw = input(f"  {prompt}{suffix}: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def _ask_checkbox(
    prompt: str,
    choices: list[tuple[str, str]],   # (display_label, value)
    defaults: list[str],
) -> list[str]:
    """Multi-select checkbox — returns list of selected values."""
    if _HAS_QUESTIONARY:
        qchoices = [
            Choice(title=label, value=val, checked=(val in defaults))
            for label, val in choices
        ]
        result = questionary.checkbox(prompt, choices=qchoices).ask()
        if result is None:
            sys.exit(0)
        return result

    # Fallback: numbered list
    print(f"\n  {prompt}")
    values = [v for _, v in choices]
    selected = set(defaults)
    for i, (label, val) in enumerate(choices, 1):
        marker = "[x]" if val in selected else "[ ]"
        print(f"    {i:2d}. {marker} {label}")
    print(dim(
        "  Enter numbers to toggle (e.g. 1,3), "
        "or press Enter to accept defaults:"
    ))
    raw = input("    > ").strip()
    if raw:
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(values):
                    v = values[idx]
                    if v in selected:
                        selected.discard(v)
                    else:
                        selected.add(v)
    return [v for _, v in choices if v in selected]


# ── Content collection ────────────────────────────────────────────────────────

def _collect_content(sub_label: str, hint: str = "") -> list[ContentLine]:
    """
    Collect multi-line content for a sub-section.
    An empty line signals end-of-input.
    """
    print(f"\n  {bold(sub_label)}")
    if hint:
        print(f"  {dim('Hint: ' + hint)}")
    print(dim(
        "  Type paragraphs or bullets "
        "(prefix  -  for bullet,    -  for sub-bullet). "
        "Empty line to finish."
    ))

    lines: list[ContentLine] = []
    while True:
        try:
            raw = input("    > ").rstrip("\n")
        except EOFError:
            break

        if not raw.strip():
            break

        # Detect indent level
        stripped = raw.lstrip()
        leading_spaces = len(raw) - len(stripped)

        is_bullet = stripped.startswith(("-", "•"))
        if is_bullet:
            text = re.sub(r'^[-•]\s*', '', stripped).strip()
            kind = BULLET_L2 if leading_spaces >= 2 else BULLET_L1
        else:
            text = stripped
            kind = PARAGRAPH

        if text:
            lines.append(ContentLine(kind=kind, text=text))

    return lines


# ── Main wizard flow ──────────────────────────────────────────────────────────

def collect_spec() -> SpecSection:
    """
    Run the full interactive wizard.
    Returns a fully-populated SpecSection ready to pass to the generator.
    """
    _print_banner()

    # ── Step 1: Project Information ───────────────────────────────────────────
    print(bold("\n  ── STEP 1 OF 6 : Project Information ──────────────────────────"))
    project_name   = _ask("Project name")
    project_number = _ask("Project number", default="")
    owner          = _ask("Owner / Client")
    engineer       = _ask("Engineer / Firm", default="")
    contractor     = _ask("Contractor", default="CONTRACTOR")

    project = ProjectInfo(
        project_name=project_name,
        project_number=project_number,
        owner=owner,
        engineer=engineer,
        contractor=contractor,
    )

    # ── Step 2: Section Identification ───────────────────────────────────────
    print(bold("\n  ── STEP 2 OF 6 : Section Identification ───────────────────────"))
    csi_number     = _ask("CSI section number (e.g., 01 11 00)", default="01 11 00")
    section_title  = _ask("Section title (e.g., SUMMARY OF WORK)").upper()

    # ── Step 3: Part 1 – General ─────────────────────────────────────────────
    print(bold("\n  ── STEP 3 OF 6 : PART 1 – GENERAL ────────────────────────────"))
    print(dim("  Select the sub-sections you need, then enter content for each."))

    subsec_choices = [
        (f"1.{num}  {title}", num)
        for num, title in PART1_SUBSECTIONS
    ]
    selected_nums = _ask_checkbox(
        "Sub-sections for Part 1 – General:",
        choices=subsec_choices,
        defaults=DEFAULT_PART1_SELECTED,
    )

    # Build a lookup: suffix → title
    ss_title_map = {num: title for num, title in PART1_SUBSECTIONS}

    part1_subsections: list[SubSection] = []
    for seq, num in enumerate(selected_nums, start=1):
        title = ss_title_map[num]
        hint  = PART1_HINTS.get(num, "")
        lines = _collect_content(f"1.{seq}  {title}", hint=hint)
        part1_subsections.append(
            SubSection(number=f"1.{seq}", title=title, lines=lines)
        )

    part1 = SpecPart(
        part_number="1",
        title="GENERAL",
        not_used=False,
        sub_sections=part1_subsections,
    )

    # ── Step 4: Part 2 – Products ────────────────────────────────────────────
    print(bold("\n  ── STEP 4 OF 6 : PART 2 – PRODUCTS ───────────────────────────"))
    part2_not_used = _ask_confirm(
        "Mark Part 2 – Products as '(NOT USED)'?", default=True
    )

    part2_subsections: list[SubSection] = []
    if not part2_not_used:
        _print_common_suggestions(COMMON_PART2_SUBSECTIONS, part="2")
        part2_subsections = _collect_freeform_subsections(part_number=2)

    part2 = SpecPart(
        part_number="2",
        title="PRODUCTS",
        not_used=part2_not_used,
        sub_sections=part2_subsections,
    )

    # ── Step 5: Part 3 – Execution ────────────────────────────────────────────
    print(bold("\n  ── STEP 5 OF 6 : PART 3 – EXECUTION ──────────────────────────"))
    part3_not_used = _ask_confirm(
        "Mark Part 3 – Execution as '(NOT USED)'?", default=False
    )

    part3_subsections: list[SubSection] = []
    if not part3_not_used:
        _print_common_suggestions(COMMON_PART3_SUBSECTIONS, part="3")
        part3_subsections = _collect_freeform_subsections(part_number=3)

    part3 = SpecPart(
        part_number="3",
        title="EXECUTION",
        not_used=part3_not_used,
        sub_sections=part3_subsections,
    )

    # ── Step 6: Output ────────────────────────────────────────────────────────
    print(bold("\n  ── STEP 6 OF 6 : Output File ──────────────────────────────────"))
    safe_title = re.sub(r'[^A-Z0-9]+', '_', section_title)[:40]
    default_fn = f"{csi_number.replace(' ', '_')}_{safe_title}.docx"
    output_path = _ask("Output filename", default=default_fn)
    if not output_path.lower().endswith(".docx"):
        output_path += ".docx"

    spec = SpecSection(
        project=project,
        csi_number=csi_number,
        section_title=section_title,
        parts=[part1, part2, part3],
        output_path=output_path,
    )

    print(green("\n  All information collected. Generating document…\n"))
    return spec


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collect_freeform_subsections(part_number: int) -> list[SubSection]:
    """
    Interactively collect an arbitrary number of sub-sections for a part.
    The user enters a title; an empty title ends the loop.
    """
    subsections: list[SubSection] = []
    seq = 1
    print(dim(
        f"  Enter sub-sections for Part {part_number}. "
        "Leave sub-section title blank to finish."
    ))
    while True:
        label = f"  Sub-section {part_number}.{seq} title"
        title = _ask(label, default="").strip().upper()
        if not title:
            break
        lines = _collect_content(f"{part_number}.{seq}  {title}")
        subsections.append(
            SubSection(
                number=f"{part_number}.{seq}",
                title=title,
                lines=lines,
            )
        )
        seq += 1
    return subsections


def _print_common_suggestions(suggestions: list[str], part: str) -> None:
    """Print a dim list of common sub-section titles for reference."""
    print(dim(f"  Common Part {part} sub-sections for reference:"))
    for name in suggestions:
        print(dim(f"    • {name}"))
    print()


def _print_banner() -> None:
    banner = r"""
  ╔═══════════════════════════════════════════════════════════╗
  ║            Specs Wizard  —  CSI MasterFormat              ║
  ╠═══════════════════════════════════════════════════════════╣
  ║   Build construction specification sections step-by-step  ║
  ╚═══════════════════════════════════════════════════════════╝
"""
    print(cyan(banner))
