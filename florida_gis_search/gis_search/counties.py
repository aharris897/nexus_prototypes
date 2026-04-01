"""All 67 Florida counties."""

FLORIDA_COUNTIES: list[str] = [
    "Alachua",
    "Baker",
    "Bay",
    "Bradford",
    "Brevard",
    "Broward",
    "Calhoun",
    "Charlotte",
    "Citrus",
    "Clay",
    "Collier",
    "Columbia",
    "DeSoto",
    "Dixie",
    "Duval",
    "Escambia",
    "Flagler",
    "Franklin",
    "Gadsden",
    "Gilchrist",
    "Glades",
    "Gulf",
    "Hamilton",
    "Hardee",
    "Hendry",
    "Hernando",
    "Highlands",
    "Hillsborough",
    "Holmes",
    "Indian River",
    "Jackson",
    "Jefferson",
    "Lafayette",
    "Lake",
    "Lee",
    "Leon",
    "Levy",
    "Liberty",
    "Madison",
    "Manatee",
    "Marion",
    "Martin",
    "Miami-Dade",
    "Monroe",
    "Nassau",
    "Okaloosa",
    "Okeechobee",
    "Orange",
    "Osceola",
    "Palm Beach",
    "Pasco",
    "Pinellas",
    "Polk",
    "Putnam",
    "Santa Rosa",
    "Sarasota",
    "Seminole",
    "St. Johns",
    "St. Lucie",
    "Sumter",
    "Suwannee",
    "Taylor",
    "Union",
    "Volusia",
    "Wakulla",
    "Walton",
    "Washington",
]


def normalize_county_name(name: str) -> str:
    """Normalize a county name for matching (strip 'County' suffix, fix casing)."""
    name = name.strip()
    if name.lower().endswith(" county"):
        name = name[: -len(" county")].strip()
    # Title-case, but preserve DeSoto / Miami-Dade / St. patterns
    return name


def find_county(name: str) -> str | None:
    """Return the canonical county name if found, else None."""
    normalized = normalize_county_name(name).lower()
    for county in FLORIDA_COUNTIES:
        if county.lower() == normalized:
            return county
    return None


def validate_counties(names: list[str]) -> tuple[list[str], list[str]]:
    """
    Validate a list of county names.

    Returns:
        (valid, invalid) — lists of canonical valid names and unrecognized inputs.
    """
    valid: list[str] = []
    invalid: list[str] = []
    for name in names:
        canonical = find_county(name)
        if canonical:
            valid.append(canonical)
        else:
            invalid.append(name)
    return valid, invalid
