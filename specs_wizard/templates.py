"""
CSI MasterFormat templates and reference data.

Provides standard sub-section lists for Part 1 – General, suggested content
hints, and a CSI division lookup table.
"""

# ── Part 1 – General sub-sections ─────────────────────────────────────────────
# Each entry: (number_suffix, title) — will be displayed as "1.X  TITLE"

PART1_SUBSECTIONS: list[tuple[str, str]] = [
    ("1", "SUMMARY"),
    ("2", "REFERENCES"),
    ("3", "DEFINITIONS"),
    ("4", "ADMINISTRATIVE REQUIREMENTS"),
    ("5", "SUBMITTALS"),
    ("6", "QUALITY ASSURANCE"),
    ("7", "DELIVERY, STORAGE, AND HANDLING"),
    ("8", "SITE CONDITIONS"),
    ("9", "WARRANTY"),
]

# Which sub-sections are checked by default
DEFAULT_PART1_SELECTED: list[str] = ["1", "5"]

# Contextual hints shown when the user enters content for each sub-section
PART1_HINTS: dict[str, str] = {
    "1": (
        "Describe the scope of work, e.g.: "
        "'Furnish and install [item] as shown on the drawings.'"
    ),
    "2": (
        "List applicable standards (AWWA, ASTM, ASCE, NFPA, etc.) "
        "and their edition years."
    ),
    "3": "Define project-specific terms used within this section.",
    "4": (
        "Coordination, pre-installation meetings, scheduling "
        "and sequencing requirements."
    ),
    "5": (
        "List required submittals: shop drawings, product data, "
        "samples, O&M manuals, test reports, etc."
    ),
    "6": (
        "Installer qualifications, mock-up requirements, "
        "field testing and inspection requirements."
    ),
    "7": (
        "Packaging requirements, delivery scheduling, "
        "on-site storage conditions and protection."
    ),
    "8": (
        "Ambient temperature / humidity limits, "
        "existing conditions to be verified in the field."
    ),
    "9": "Warranty period and coverage requirements.",
}

# ── Common Part 2 / Part 3 sub-section starters ───────────────────────────────

COMMON_PART2_SUBSECTIONS: list[str] = [
    "MATERIALS",
    "EQUIPMENT",
    "COMPONENTS",
    "MIXES",
    "FABRICATION",
    "FINISHES",
    "SOURCE QUALITY CONTROL",
]

COMMON_PART3_SUBSECTIONS: list[str] = [
    "EXAMINATION",
    "PREPARATION",
    "INSTALLATION",
    "CONSTRUCTION",
    "APPLICATION",
    "ERECTION",
    "FIELD QUALITY CONTROL",
    "ADJUSTING",
    "CLEANING",
    "PROTECTION",
    "CLOSEOUT ACTIVITIES",
]

# ── CSI MasterFormat division index (abbreviated) ─────────────────────────────

CSI_DIVISIONS: dict[str, str] = {
    "00": "Procurement and Contracting Requirements",
    "01": "General Requirements",
    "02": "Existing Conditions",
    "03": "Concrete",
    "04": "Masonry",
    "05": "Metals",
    "06": "Wood, Plastics, and Composites",
    "07": "Thermal and Moisture Protection",
    "08": "Openings",
    "09": "Finishes",
    "10": "Specialties",
    "11": "Equipment",
    "12": "Furnishings",
    "13": "Special Construction",
    "14": "Conveying Equipment",
    "21": "Fire Suppression",
    "22": "Plumbing",
    "23": "Heating, Ventilating, and Air Conditioning (HVAC)",
    "25": "Integrated Automation",
    "26": "Electrical",
    "27": "Communications",
    "28": "Electronic Safety and Security",
    "31": "Earthwork",
    "32": "Exterior Improvements",
    "33": "Utilities",
    "34": "Transportation",
    "35": "Waterway and Marine",
    "40": "Process Integration",
    "41": "Material Processing and Handling Equipment",
    "43": "Gas and Liquid Handling, Purification, and Storage Equipment",
    "44": "Pollution and Waste Control Equipment",
    "46": "Water and Wastewater Equipment",
    "48": "Electrical Power Generation",
}
