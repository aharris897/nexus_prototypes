"""
Interactive CLI for the GIS Data Search Tool.

Flow:
  1. County selection (interactive picker or --counties argument)
  2. Per-county GIS search via Claude AI (with live status output)
  3. Results displayed grouped by county → category
  4. User selects datasets to download (multi-select)
  5. Downloads proceed with progress bars
"""

import os
import sys
from collections import defaultdict
from typing import Sequence

try:
    import questionary
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False

from .agent import GISSearchAgent
from .counties import FLORIDA_COUNTIES, validate_counties
from .downloader import download_datasets
from .models import CATEGORY_ORDER, GISDataset


# ── Colour helpers (ANSI, disabled on non-TTY) ─────────────────────────────────

def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _is_tty():
        return f"\033[{code}m{text}\033[0m"
    return text


def bold(t: str) -> str:    return _c("1", t)
def cyan(t: str) -> str:    return _c("36", t)
def green(t: str) -> str:   return _c("32", t)
def yellow(t: str) -> str:  return _c("33", t)
def red(t: str) -> str:     return _c("31", t)
def dim(t: str) -> str:     return _c("2", t)


# ── Entry point ────────────────────────────────────────────────────────────────

def run_cli(
    counties: list[str] | None = None,
    output_dir: str = "./gis_downloads",
    no_download: bool = False,
) -> None:
    """Main CLI entry point called from main.py."""
    _print_banner()

    # ── 1. Validate / select counties ─────────────────────────────────────────
    selected_counties = _resolve_counties(counties)
    if not selected_counties:
        print(red("No counties selected. Exiting."))
        sys.exit(0)

    print(
        f"\n{bold('Counties to search:')} "
        + ", ".join(cyan(c) for c in selected_counties)
    )

    # ── 2. Check API key ───────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            red("\nERROR: ANTHROPIC_API_KEY environment variable is not set.\n")
            + "Export your key before running:\n"
            + dim("  export ANTHROPIC_API_KEY=sk-ant-...")
        )
        sys.exit(1)

    # ── 3. Search each county ──────────────────────────────────────────────────
    all_datasets: dict[str, list[GISDataset]] = {}

    agent = GISSearchAgent(on_status=lambda msg: print(f"  {msg}"))

    for county in selected_counties:
        print(f"\n{bold('━' * 60)}")
        print(f"{bold('Searching:')} {cyan(county + ' County')}")
        print(bold("━" * 60))

        datasets = agent.search(county)
        all_datasets[county] = datasets

        if datasets:
            _print_datasets_table(county, datasets)
        else:
            print(yellow("  No datasets found for this county."))

    # ── 4. Summary ─────────────────────────────────────────────────────────────
    total = sum(len(v) for v in all_datasets.values())
    print(f"\n{bold('━' * 60)}")
    print(f"{bold('Search complete.')}  {green(str(total))} dataset(s) found across "
          f"{len(selected_counties)} county/counties.")
    print(bold("━" * 60))

    if total == 0:
        print(yellow("\nNo datasets to download. Try different counties."))
        return

    if no_download:
        print(dim("\n--no-download flag set. Skipping download step."))
        return

    # ── 5. Select datasets to download ────────────────────────────────────────
    chosen = _select_datasets(all_datasets)
    if not chosen:
        print(yellow("\nNo datasets selected. Exiting."))
        return

    print(f"\n{bold(str(len(chosen)))} dataset(s) selected for download.")
    print(f"Output directory: {cyan(output_dir)}\n")

    # ── 6. Download ────────────────────────────────────────────────────────────
    download_datasets(
        chosen,
        output_dir=output_dir,
        on_status=print,
    )

    downloaded = [d for d in chosen if d.local_path]
    print(
        f"\n{green('Done.')}  "
        f"{green(str(len(downloaded)))}/{len(chosen)} dataset(s) downloaded "
        f"to {cyan(output_dir)}/"
    )


# ── County selection ───────────────────────────────────────────────────────────

def _resolve_counties(counties: list[str] | None) -> list[str]:
    """Validate provided counties or prompt the user to pick interactively."""
    if counties:
        valid, invalid = validate_counties(counties)
        if invalid:
            print(yellow(f"Warning: unrecognised county name(s): {', '.join(invalid)}"))
            print(dim("  Valid Florida counties: " + ", ".join(FLORIDA_COUNTIES[:10]) + " …"))
        return valid

    # Interactive selection
    if _HAS_QUESTIONARY:
        return _pick_counties_questionary()
    else:
        return _pick_counties_basic()


def _pick_counties_questionary() -> list[str]:
    """Use questionary checkbox for county selection."""
    import questionary  # noqa: PLC0415

    print(f"\n{bold('Select Florida counties to search')} (space to toggle, enter to confirm):")
    selected = questionary.checkbox(
        "Counties:",
        choices=FLORIDA_COUNTIES,
    ).ask()
    return selected or []


def _pick_counties_basic() -> list[str]:
    """Fallback numbered-list county picker when questionary is unavailable."""
    print(f"\n{bold('Available Florida Counties:')}\n")
    for i, county in enumerate(FLORIDA_COUNTIES, 1):
        print(f"  {i:3d}. {county}")

    print(
        f"\nEnter county numbers separated by commas "
        f"(e.g. {dim('1,5,12')}) or county names:\n"
    )
    raw = input("  > ").strip()
    if not raw:
        return []

    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(FLORIDA_COUNTIES):
                selected.append(FLORIDA_COUNTIES[idx])
            else:
                print(yellow(f"  Skipping out-of-range index: {token}"))
        else:
            valid, _ = validate_counties([token])
            if valid:
                selected.extend(valid)
            else:
                print(yellow(f"  Unrecognised county: {token}"))
    return selected


# ── Results display ────────────────────────────────────────────────────────────

def _print_datasets_table(county: str, datasets: list[GISDataset]) -> None:
    """Print a formatted table of datasets grouped by category."""
    by_category: dict[str, list[GISDataset]] = defaultdict(list)
    for ds in datasets:
        by_category[ds.category].append(ds)

    # Display in priority order
    for cat in CATEGORY_ORDER:
        if cat not in by_category:
            continue
        items = by_category[cat]
        label = items[0].category_label
        print(f"\n  {bold(cyan(label))} ({len(items)} dataset(s))")
        for ds in items:
            dl_flag = green("⬇ direct") if ds.direct_download else dim("🔗 portal")
            print(f"    • {bold(ds.name)}")
            print(f"      {dim(ds.description)}")
            print(f"      Format: {yellow(ds.format_label)}  |  {dl_flag}  |  Source: {ds.source}")
            print(f"      {dim(ds.url[:90] + ('…' if len(ds.url) > 90 else ''))}")


# ── Dataset selection ──────────────────────────────────────────────────────────

def _select_datasets(
    all_datasets: dict[str, list[GISDataset]],
) -> list[GISDataset]:
    """Present a combined list of all found datasets and let the user choose."""
    flat: list[GISDataset] = []
    for county_datasets in all_datasets.values():
        flat.extend(county_datasets)

    if not flat:
        return []

    print(f"\n{bold('Select datasets to download:')}")

    if _HAS_QUESTIONARY:
        return _select_datasets_questionary(flat)
    else:
        return _select_datasets_basic(flat)


def _select_datasets_questionary(flat: list[GISDataset]) -> list[GISDataset]:
    """Multi-select with questionary, grouped by county + category for readability."""
    import questionary  # noqa: PLC0415
    from questionary import Choice, Separator  # noqa: PLC0415

    choices: list = []
    prev_county = None

    # Sort by county, then category priority
    cat_priority = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    sorted_flat = sorted(
        flat,
        key=lambda d: (d.county, cat_priority.get(d.category, 99), d.name),
    )

    for ds in sorted_flat:
        if ds.county != prev_county:
            choices.append(Separator(f"\n── {ds.county} County ──"))
            prev_county = ds.county
        dl_tag = "⬇" if ds.direct_download else "🔗"
        label = f"{dl_tag} [{ds.category_label}] {ds.name}  ({ds.format_label})"
        choices.append(Choice(title=label, value=ds))

    selected = questionary.checkbox(
        "Datasets (space to toggle, enter to confirm):",
        choices=choices,
        instruction="(space=select, a=all, i=invert, enter=confirm)",
    ).ask()

    return selected or []


def _select_datasets_basic(flat: list[GISDataset]) -> list[GISDataset]:
    """Fallback numbered-list selector when questionary is unavailable."""
    print()
    cat_priority = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    sorted_flat = sorted(
        flat,
        key=lambda d: (d.county, cat_priority.get(d.category, 99), d.name),
    )

    for i, ds in enumerate(sorted_flat, 1):
        dl_tag = "⬇" if ds.direct_download else "🔗"
        print(
            f"  {i:3d}. {dl_tag} [{ds.county}] [{ds.category_label}] "
            f"{ds.name}  ({ds.format_label})"
        )

    print(
        f"\nEnter numbers to download (e.g. {dim('1,3,5')}), "
        f"{dim('all')} for everything, or {dim('enter')} to skip:\n"
    )
    raw = input("  > ").strip().lower()

    if not raw:
        return []
    if raw == "all":
        return sorted_flat

    chosen: list[GISDataset] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(sorted_flat):
                chosen.append(sorted_flat[idx])
            else:
                print(yellow(f"  Skipping out-of-range: {token}"))
    return chosen


# ── Banner ─────────────────────────────────────────────────────────────────────

def _print_banner() -> None:
    banner = r"""
  ╔═══════════════════════════════════════════════════════════╗
  ║          Florida GIS Data Search Tool  (Claude AI)        ║
  ╠═══════════════════════════════════════════════════════════╣
  ║  Finds parcels · boundaries · water/wastewater/reclaimed  ║
  ╚═══════════════════════════════════════════════════════════╝
"""
    print(cyan(banner))
