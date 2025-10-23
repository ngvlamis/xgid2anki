# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.pipeline

Orchestrates the end‑to‑end flow:
  1) Run GNUBG analysis for the provided XGIDs.
  2) Parse the GNUBG output into structured position data.
  3) Augment positions with arrow overlays for board rendering.
  4) Render board SVGs via bglog and bundle them into an Anki deck.
"""

from __future__ import annotations

from .xgid2svg import xgid2svg
from .parse_gnubg_eval import parse_gnubg_eval
from .build_deck import build_deck
from .analyze_positions import analyze_positions

from pathlib import Path

import shutil
import logging

logger = logging.getLogger(__name__)


def generate_arrows(data):
    """
    For positions with a move decision, we extend the list of xgids we iterate over by adding an xgid together with move, allowing rendering of the board image with arrows.
    """
    xgid_with_arrows = []
    for entry in data:
        id = entry["xgid"]
        xgid_with_arrows.append([id])
        if "moves" in entry:
            for move in entry["moves"]:
                arrows_to_draw = " ".join(move["move"])
                xgid_with_arrows.append([id, arrows_to_draw])

    return xgid_with_arrows


def xgid2anki_pipeline(
    xgids: list[str],
    deck_name: str,
    cores: int,
    plies: int,
    cube_ply: int,
    bglog_path: Path,
    board_theme: dict,
    keep_svg: bool,
    output_path: Path,
) -> int:
    """Run the full pipeline, converting a set of XGIDs to an Anki deck
    Parameters
    ----------
    xgids
        Iterable of XGID strings to analyze.
    deck_name
        Name for the Anki deck.
    output_path
        Destination path for the generated ``.apkg`` file.
    bglog_path
        Filesystem path to ``bglog.js`` (used by the renderer).
    board_theme
        bglog theme to be used in board rendering.
    plies
        Search depth for move decisions.
    cube_ply
        Search depth for cube decisions.
    keep_svg
        If ``True``, keep the generated board SVG assets.
    cores
        Number of cores to be used in gnubg analysis.

    Returns
    -------
    int
        ``0`` on success. Non‑zero codes may be used by callers for failures.
    """

    # Analyze positions with GNUBG
    logger.info(f'Building deck "{deck_name}" with {len(xgids)} positions')
    logger.info(
        "Analyzing positions with GNUBG (move plies set to %d and cube plies set to %d)…",
        plies,
        cube_ply,
    )
    gnubg_analysis, rc = analyze_positions(xgids, cores, plies, cube_ply)
    logger.info("GNUBG analysis complete.")

    if rc != 0:
        logger.warning(
            "Analysis may have encountered errors (rc=%d). Will attempt to continue but make sure to confirm output is as desired.",
            rc,
        )

    # Parse GNUBG analysis into useable dictionary
    logger.info("Parsing GNUBG analysis.")
    position_data = parse_gnubg_eval(gnubg_analysis)

    # Generate iterable consisting of xgids together with arrow data for move positions
    xgids_w_arrows = generate_arrows(position_data)

    # Generate board images
    logger.info("Will now generate SVGs for board positions …")
    xgid2svg(xgids_w_arrows, bglog_path, board_theme)

    # Build Anki deck using genanki library
    logger.info("Building anki package …")
    media_folder = bglog_path.parent / "board-images"
    build_deck(position_data, deck_name, media_folder, output_path, plies, cube_ply)

    # Delete or keep svg images based on user preference; if kept, give user folder path
    board_images_folder = bglog_path.parent / "board-images"
    if not keep_svg:
        if board_images_folder.exists() and board_images_folder.is_dir():
            shutil.rmtree(board_images_folder)
            logger.info("Removed board images.")
    else:
        logger.info("Saved board images can be found in %s", board_images_folder)

    logger.info("Process complete.")
    return 0
