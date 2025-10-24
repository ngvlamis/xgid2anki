# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.cli
CLI for generating Anki decks from backgammon positions (XGIDs).

Flow:
1) Parse arguments
2) Check for dependencies: download headless chromium browser and/or bglog if missing
3) Load theme for board images
4) Collect XGIDs from -i/--input (literals and/or files), or interactively if omitted.
5) Validate and deduplicate XGIDs.
6) Run the deck build pipeline.

Entrypoint:
- main() -> int
"""

from __future__ import annotations

import argparse
import logging
import sys
import shutil
import json
from pathlib import Path
from typing import Iterable, List, Tuple

# Local imports
from .validate_xgid import validate_xgid
from .download_bglog import download_bglog
from .pipeline import xgid2anki_pipeline
from .ensure_headless_chromium import ensure_headless_chromium

try:
    import yaml  # optional, only needed if --config is used
except Exception:  # pragma: no cover
    yaml = None


class ConfigError(Exception):
    """Raised when there is an error loading or parsing the user files specified in the config."""

    pass


def load_yaml_config(cfg_path: Path) -> dict:
    """Load YAML config as a mapping.

    - Treats empty files as {}.
    - Ensures top-level is a mapping; avoids accidental list/str configs.
    """
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"ERROR: Error parsing YAML config {cfg_path}:\n{e}") from e
    except OSError as e:
        raise ConfigError(f"ERROR: Cannot read config file {cfg_path}:\n{e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"ERROR: Top-level YAML must be a mapping: {cfg_path}")

    return data


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Parse args with optional YAML defaults via --config.

    Two-stage parse:
      1) Pre-parse to capture --config
      2) Load defaults from YAML (if any) and feed into full parser via set_defaults

    Post-parse: compute dynamic defaults (e.g., cores) only if not provided.
    """

    # (1) Pre-parse for --config
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument(
        "--config",
        help="Path to a YAML file with defaults (keys must match CLI flags).",
        type=Path,
    )
    pre_args, remaining = pre.parse_known_args(argv)

    defaults: dict = {}
    if pre_args.config:
        if yaml is None:
            raise SystemExit(
                "--config requires PyYAML to be installed (pip install pyyaml)."
            )
        if not pre_args.config.exists():
            raise SystemExit(f"--config not found: {pre_args.config}")

        try:
            defaults = load_yaml_config(pre_args.config)
        except ConfigError as e:
            logging.error("ERROR: %s", str(e))
            raise SystemExit(1)

    # (2) Full parser: knows all flags; seed with YAML defaults
    parser = argparse.ArgumentParser(
        prog="xgid2anki",
        description=(
            "Generate Anki decks for backgammon positions from XGIDs. "
            "Provide one or more XGIDs or one or more files (one XGID per line)."
        ),
        parents=[pre],
    )

    # Positional form (zero or more)
    parser.add_argument(
        "paths_or_xgids",
        nargs="*",
        metavar="PATH_OR_XGID",
        help="(Positional) One or more file paths and/or literal XGIDs; equivalent to --input.",
    )

    # I/O group
    io_group = parser.add_argument_group("Input / Output")
    io_group.add_argument(
        "-i",
        "--input",
        metavar="PATH_OR_XGID",
        nargs="*",
        help="One or more file paths (lines of XGIDs) and/or literal XGIDs.",
    )
    io_group.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory or .apkg file (default: current working dir)",
    )

    # Deck & Analysis Options
    user_pref_group = parser.add_argument_group("Deck & Analysis Options")
    user_pref_group.add_argument(
        "-d",
        "--deck-name",
        help="Name for the output Anki deck (required; will prompt if omitted).",
        type=str,
    )
    user_pref_group.add_argument(
        "-p",
        "--plies",
        help="Number of plies for analysis (0–4, default: 3).",
        type=int,
        default=3,
        choices=range(0, 5),
    )
    user_pref_group.add_argument(
        "--cube-plies",
        help="Number of plies for cube analysis (0–4, defaults to the value from --plies).",
        type=int,
        choices=range(0, 5),
    )
    user_pref_group.add_argument(
        "-b",
        "--bear-off",
        help="Set bear-off direction (cw or ccw, default: cw)",
        type=str,
        choices=["cw", "ccw"],
    )
    user_pref_group.add_argument(
        "-t",
        "--theme",
        help=(
            "Path to a custom bglog board theme (optional).\n"
            "You can create your own theme at https://nt.bglog.org/NT.html.\n"
            "Theme should be saved as a JSON file."
        ),
        type=Path,
    )
    user_pref_group.add_argument(
        "-c",
        "--cores",
        help="Worker processes (default: system CPU count - 1)",
        type=int,
    )
    user_pref_group.add_argument(
        "-k",
        "--keep_svg",
        help="Keep the SVGs generated during the creation of the deck.",
        action="store_true",
    )
    user_pref_group.add_argument(
        "-q", "--quiet", help="Reduce verbosity.", action="store_true"
    )

    # Apply YAML defaults
    parser.set_defaults(**defaults)

    # Parse remaining flags
    args = parser.parse_args(remaining)

    # Dynamic defaults — compute only if user/config didn’t supply a value
    if args.cores is None:
        import os

        cores = os.cpu_count() or 1
        args.cores = max(1, cores - 1)

    return args


def configure_logging(quiet: bool) -> None:
    """
    Configure logging, using warning level for quiet mode and info level otherwise.
    """
    if quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(message)s")


def ensure_gnubg_is_installed():
    """
    Check if GNU Backgammon is installed, exit if not.
    """

    if shutil.which("gnubg") is not None:
        logging.info("GNU Backgammon (gnubg) found.")
    else:
        raise SystemExit(
            "ERROR: GNU Backgammon (gnubg) not found in PATH. Please install it first."
        )


def prompt_yes_no(question: str, default: bool | None = None) -> bool:
    """
    Ask a yes/no question via input().
    - default=True/False sets the default on empty input.
    - default=None forces explicit y/n.
    - If stdin is not a TTY (e.g., piped/CI), returns default if given; otherwise False.
    - Handles Ctrl+C/EOF by returning False.
    """
    if not sys.stdin.isatty():
        return default if default is not None else False

    if default is True:
        suffix = " [Y/n] "
    elif default is False:
        suffix = " [y/N] "
    else:
        suffix = " [y/n] "

    while True:
        try:
            ans = input(question + suffix).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()  # newline for a clean prompt
            return False

        if not ans and default is not None:
            return default
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def load_theme(json_path: Path | None, direction: str | None) -> dict:
    """
    Validate and load a theme JSON file, falling back to default if invalid.
    If no theme JSON path is present, load default theme.
    In each case, check if user set bear-off direction flag, and use this flag
    to override direction specified in the theme.
    """

    user_theme: dict = {}
    default_theme_path = Path(__file__).parent / "themes" / "default_theme.json"
    with default_theme_path.open(encoding="utf-8") as f:
        default_theme = json.load(f)

    if json_path:
        try:
            with json_path.open("r", encoding="utf-8") as f:
                user_theme = json.load(f)
        except FileNotFoundError:
            logging.error("ERROR: Theme file not found: %s", json_path)
        except IsADirectoryError:
            logging.error("ERROR: Theme path is a directory, not a file: %s", json_path)
        except json.JSONDecodeError as e:
            logging.error(
                "ERROR: Invalid JSON in theme file (%s:%s): %s",
                e.lineno,
                e.colno,
                e.msg,
            )
        except Exception as e:
            logging.error("ERROR: Unexpected error reading theme file: %s", e)
        else:
            # Loaded successfully; skip default fallback logic entirely
            # Fill in any missing attributes in the user's theme with the defaults
            logging.info("Successfully loaded user theme file.")
            merged_theme = default_theme | user_theme
            if direction:
                if direction == "ccw":
                    merged_theme["direction"] = False
                else:
                    merged_theme["direction"] = True
            return merged_theme

        # JSON was invalid or could not be read
        if not prompt_yes_no("Do you want to continue with the default theme?", False):
            raise ConfigError("Aborting at user request")

    # Invalid JSON and user wants to continue with default
    logging.info("Using default theme.")

    if direction:
        if direction == "ccw":
            default_theme["direction"] = False
        else:
            default_theme["direction"] = True

    return default_theme


def determine_out_path(out_path: Path | None) -> Path:
    # Determine output directory
    if out_path:
        if not out_path.exists() or not out_path.is_dir():
            logging.error(
                "ERROR: Specified path for ouput is invalid (given path: %s).", out_path
            )
            out_msg = "Continue with saving package in current directory?"
            if prompt_yes_no(out_msg, True):
                logging.info("Continue with current directory.")
                return Path.cwd()
            else:
                raise ConfigError("Aborting at user request.")
        else:
            return out_path
    else:
        return Path.cwd()


def prompt_for_deck_name(existing: str | None = None) -> str:
    """
    Return a non-empty deck name. If 'existing' is empty/None,
    re-prompt until the user enters a non-empty value.
    """
    name = (existing or "").strip()
    while not name:
        name = input("Enter a name for the Anki deck: ").strip()
    return name


def interactive_prompt(deck_name: str | None = None) -> Tuple[list[str], str]:
    """
    Ask the user to provide XGIDs (single or file) and ensure we have a deck name.
    Returns (xgids, deck_name).
    """
    print("No XGIDs or files provided.")
    print("Choose an option:")
    print("  1) Provide a single XGID")
    print("  2) Provide a path to a text file of XGIDs (one per line)")

    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            x = input("Enter XGID: ").strip()
            if not x:
                print("Empty XGID. Please try again.")
                continue
            xgids = [x]
            break
        elif choice == "2":
            p = input("Path to file: ").strip()
            try:
                xgids = read_xgids_file(Path(p))
                if not xgids:
                    print("No XGIDs found in file. Please try again.")
                    continue
                break
            except Exception as e:
                print(f"Error reading file: {e}")
        else:
            print("Please enter 1 or 2.")

    deck_name = prompt_for_deck_name(deck_name)
    return xgids, deck_name


def read_xgids_file(path: Path) -> list[str]:
    """
    Read XGIDs from a file. Ignores blank lines and lines starting with '#'.
    """
    path = path.expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    xgids: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            xgids.append(s)
    return xgids


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def detect_and_collect(inputs: list[str]) -> list[str]:
    """Detect whether each input is a file or an inline XGID, then combine (concatenate)."""
    all_xgids: list[str] = []
    for item in inputs:
        p = Path(item).expanduser()
        if p.exists() and p.is_file():
            logging.debug(f"Reading XGIDs from file: {p}")
            all_xgids.extend(read_xgids_file(p))
        else:
            logging.debug(f"Treating as XGID: {item}")
            all_xgids.append(item)
    return all_xgids


def main(argv: List[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except Exception as e:
        logging.error(str(e))
        return 2

    configure_logging(args.quiet)

    logging.info("Checking for dependencies:")

    # Check if gnubg is installed
    try:
        ensure_gnubg_is_installed()
    except Exception as e:
        logging.error(e)
        return 127

    # Ensure chromium browswer installation for playwright
    try:
        ensure_headless_chromium()
    except Exception:
        return 1

    # Ensure a local and patched version of bglog exists
    try:
        bgpath = download_bglog()
    except Exception:
        return 1

    # Load board theme, using any user defined theme attributes set in args
    try:
        theme = load_theme(args.theme, args.bear_off)
    except Exception as e:
        logging.error(str(e))
        return 2

    # Determine output path
    try:
        output_path = determine_out_path(args.output)
    except Exception as e:
        logging.error(str(e))
        return 2

    # Collect candidates
    if args.input:
        candidates = detect_and_collect(args.input)
        deck_name = prompt_for_deck_name(args.deck_name)  # ← ensures re-prompt if empty
    else:
        candidates, deck_name = interactive_prompt(deck_name=args.deck_name)

    # Normalize + validate + dedupe
    cleaned: list[str] = []
    error_count = 0
    for raw in candidates:
        x, errors = validate_xgid(raw.strip())
        if errors:
            logging.warning(
                "Skipping invalid XGID: %r, as it contains the following errors:\n•%s",
                x,
                "\n•".join(errors),
            )
            error_count += 1
            continue
        cleaned.append(x)

    cleaned = dedupe_preserve_order(cleaned)
    if not cleaned:
        logging.error("No valid XGIDs to process.")
        return 1

    if error_count > 0:
        msg = f"There were {error_count} invalid XGIDs. Do you want to continue building the deck with the remaining {len(cleaned)} XGIDs?"
        if prompt_yes_no(msg, False):
            logging.info("Continuing with %d valid XGID(s).", len(cleaned))
        else:
            logging.error("Aborting at user request.")
            return 2

    if args.cube_plies is None:
        cube_plies = args.plies
    else:
        cube_plies = args.cube_plies

    return xgid2anki_pipeline(
        xgids=cleaned,
        deck_name=deck_name,
        cores=args.cores,
        plies=args.plies,
        cube_ply=cube_plies,
        bglog_path=bgpath,
        board_theme=theme,
        keep_svg=args.keep_svg,
        output_path=output_path,
    )


if __name__ == "__main__":
    sys.exit(main())
