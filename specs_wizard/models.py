"""
Data models for the Specs Wizard.

A SpecSection represents one complete CSI MasterFormat specification section,
composed of ProjectInfo, three SpecParts (General / Products / Execution),
and each Part containing SubSections with ContentLines.
"""

from dataclasses import dataclass, field

# Content line kinds
PARAGRAPH = "para"
BULLET_L1 = "bullet1"
BULLET_L2 = "bullet2"


@dataclass
class ContentLine:
    """One line of content inside a sub-section."""
    kind: str   # PARAGRAPH, BULLET_L1, or BULLET_L2
    text: str


@dataclass
class SubSection:
    """A numbered sub-section (e.g., 1.1 SUMMARY)."""
    number: str            # e.g., "1.1"
    title: str             # e.g., "SUMMARY"
    lines: list[ContentLine] = field(default_factory=list)


@dataclass
class SpecPart:
    """One of the three parts of a spec section (GENERAL / PRODUCTS / EXECUTION)."""
    part_number: str       # "1", "2", or "3"
    title: str             # "GENERAL", "PRODUCTS", "EXECUTION"
    not_used: bool = False
    sub_sections: list[SubSection] = field(default_factory=list)


@dataclass
class ProjectInfo:
    """Project-level metadata written to the document header/footer."""
    project_name: str
    project_number: str
    owner: str
    engineer: str
    contractor: str


@dataclass
class SpecSection:
    """The complete data model for one specification section."""
    project: ProjectInfo
    csi_number: str        # e.g., "01 11 00"
    section_title: str     # e.g., "SUMMARY OF WORK"
    parts: list[SpecPart] = field(default_factory=list)
    output_path: str = ""
