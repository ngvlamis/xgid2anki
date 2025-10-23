# -*- coding: utf-8 -*-
# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.build_deck
--------------------

Assemble an Anki deck from analyzed backgammon positions.

Given structured position data (including board image paths and cube/move
evaluations), this module:
  1. Generates flashcards according to template type (move, cube, take/pass).
  2. Packages all cards and associated media into an `.apkg` file via genanki.
  3. Handles deck naming, media linking, and export path management.

Intended to be called from :func:`xgid2anki.pipeline.xgid2anki_pipeline`; emits progress via
:mod:`logging` but performs no console I/O.
"""

import genanki
from pathlib import Path
from .id_scheme import stable_deck_id, stable_model_id
from .xgid2svg import sanitize_filename

import logging

logger = logging.getLogger(__name__)

# ---------- Defaults ----------
ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
MOVE_BACK_TEMPLATE = TEMPLATES_DIR / "move_back.html"
MOVE_FRONT_TEMPLATE = TEMPLATES_DIR / "move_front.html"
CUBE_BACK_TEMPLATE = TEMPLATES_DIR / "cube_back.html"
CUBE_FRONT_TEMPLATE = TEMPLATES_DIR / "cube_front.html"
TAKEPASS_BACK_TEMPLATE = TEMPLATES_DIR / "takepass_back.html"
TAKEPASS_FRONT_TEMPLATE = TEMPLATES_DIR / "takepass_front.html"
COMMON_CSS = TEMPLATES_DIR / "shared_styles.css"

# ---------- Models (note types) ----------
# You can change the *display* names safely; IDs are derived deterministically below.
MOVE_MODEL_NAME = "BG • Move Decision"
CUBE_MODEL_NAME = "BG • Cube Decision"
TAKEPASS_MODEL_NAME = "BG • Take/Pass Decision"

# Bump these when fields/templates change incompatibly (mint new Model IDs).
MOVE_MODEL_SCHEMA = "v1"
CUBE_MODEL_SCHEMA = "v1"

# ---- IDs ----
MODEL_NAME = "BG • Demo Model"
MODEL_SCHEMA = "v1"
CUBE_MODEL_ID = stable_model_id(CUBE_MODEL_NAME, schema_version=MODEL_SCHEMA)
MOVE_MODEL_ID = stable_model_id(MOVE_MODEL_NAME, schema_version=MODEL_SCHEMA)
TAKEPASS_MODEL_ID = stable_model_id(TAKEPASS_MODEL_NAME, schema_version=MODEL_SCHEMA)


# ---- Define a note types (models) for Move and Cube decisions ----

MoveModel = genanki.Model(
    MOVE_MODEL_ID,
    name=MOVE_MODEL_NAME,
    fields=[
        {"name": "XGID"},
        {"name": "DeckName"},
        {"name": "PositionImage"},
        {"name": "Move1"},
        {"name": "Move1EMG"},
        {"name": "Move1SVG"},
        {"name": "Move2"},
        {"name": "Move2EMG"},
        {"name": "Move2SVG"},
        {"name": "Move3"},
        {"name": "Move3EMG"},
        {"name": "Move3SVG"},
        {"name": "Move4"},
        {"name": "Move4EMG"},
        {"name": "Move4SVG"},
        {"name": "Move5"},
        {"name": "Move5EMG"},
        {"name": "Move5SVG"},
        {"name": "Move6"},
        {"name": "Move6EMG"},
        {"name": "Move6SVG"},
        {"name": "WPercentage"},
        {"name": "GPercentage"},
        {"name": "BGPercentage"},
        {"name": "OppGPercentage"},
        {"name": "OppBGPercentage"},
        {"name": "Equity"},
        {"name": "Plies"},
    ],
    templates=[
        {
            "name": "Move Decision Card",
            "qfmt": MOVE_FRONT_TEMPLATE.read_text(encoding="utf-8"),
            "afmt": MOVE_BACK_TEMPLATE.read_text(encoding="utf-8"),
        },
    ],
    css=COMMON_CSS.read_text(encoding="utf-8"),
)


CubeModel = genanki.Model(
    CUBE_MODEL_ID,
    name=CUBE_MODEL_NAME,
    fields=[
        {"name": "XGID"},
        {"name": "DeckName"},
        {"name": "BoardImage"},
        {"name": "ND EMG"},
        {"name": "DT EMG"},
        {"name": "WPercentage"},
        {"name": "WGPercentage"},
        {"name": "WBGPercentage"},
        {"name": "OppGPercentage"},
        {"name": "OppBGPercentage"},
        {"name": "Equity"},
        {"name": "Plies"},
    ],
    templates=[
        {
            "name": "Cube Decision Card",
            "qfmt": CUBE_FRONT_TEMPLATE.read_text(encoding="utf-8"),
            "afmt": CUBE_BACK_TEMPLATE.read_text(encoding="utf-8"),
        },
    ],
    css=COMMON_CSS.read_text(encoding="utf-8"),
)

TakePassModel = genanki.Model(
    TAKEPASS_MODEL_ID,
    name=TAKEPASS_MODEL_NAME,
    fields=[
        {"name": "XGID"},
        {"name": "DeckName"},
        {"name": "BoardImage"},
        {"name": "DT EMG"},
        {"name": "WPercentage"},
        {"name": "WGPercentage"},
        {"name": "WBGPercentage"},
        {"name": "OppGPercentage"},
        {"name": "OppBGPercentage"},
        {"name": "Equity"},
        {"name": "Plies"},
    ],
    templates=[
        {
            "name": "Take/Pass Decision Card",
            "qfmt": TAKEPASS_FRONT_TEMPLATE.read_text(encoding="utf-8"),
            "afmt": TAKEPASS_BACK_TEMPLATE.read_text(encoding="utf-8"),
        },
    ],
    css=COMMON_CSS.read_text(encoding="utf-8"),
)


def init_deck(deck_name):
    # --- Get id for deck --- #
    deck_id = stable_deck_id(deck_name)

    # ---- Create the deck ----
    return genanki.Deck(deck_id, deck_name)


def make_note(entry, name, plies, cplies):
    # --- Initiate field collection, which starts the same regardless of model --- #
    xgid = entry["xgid"]
    board_image = f'<img src="{sanitize_filename(xgid)}.svg">'
    fields = [xgid, name, board_image]

    # eval is common to both cube and moves
    # field entries must be strings
    eval = [str(x) for x in entry["eval"]]

    if entry["action"] == "move":
        # --- Parse formatted gnubg data and record in relevant fields --- #
        moves = entry["moves"]

        for i in range(6):  # always 6 "slots"
            if i < len(moves):
                m = moves[i]
                mv_str = " ".join(m["move"])
                emg_str = str(m["emg"])
                xgid_part = sanitize_filename(xgid)
                move_part = sanitize_filename("m".join(m["move"]))
                filename = f"{xgid_part}_{move_part}.svg"
                # filename = f"{xgid}-{'_'.join(m['move'])}.svg"
                file_str = f'<img src="{sanitize_filename(filename)}">'
                fields.extend([mv_str, emg_str, file_str])
            else:
                fields.extend(["", "", ""])

        fields.extend(eval)
        fields.append(plies)
        model = MoveModel

    elif entry["action"] == "cube":
        # --- Parse formatted gnubg data and record in relevant fields --- #
        nd_emg = str(entry["nd_emg"])
        dt_emg = str(entry["dt_emg"])

        fields.extend([nd_emg, dt_emg])
        fields.extend(eval)
        fields.append(cplies)

        model = CubeModel
    elif entry["action"] == "takepass":
        # --- Parse formatted gnubg data and record in relevant fields --- #
        dt_emg = str(entry["dt_emg"])

        fields.append(dt_emg)
        fields.extend(eval)
        fields.append(cplies)

        model = TakePassModel

    return genanki.Note(
        model=model,
        fields=fields,
    )


def build_deck_package(d, media_dir, name, out_path):
    pkg = genanki.Package(d)

    # Collect svgs for the package
    svgs = sorted(media_dir.glob("*.svg"))
    pkg.media_files = [str(svg) for svg in svgs]

    # Write Anki deck to file
    out = out_path / sanitize_filename(name + ".apkg")
    pkg.write_to_file(out.as_posix())
    logger.info("Successfully created anki deck.")
    logger.info("Anki pacakged saved to %s", out_path)


def build_deck(
    data: dict,
    name: str,
    board_directory: Path,
    out_directory: Path,
    plies: int,
    cplies: int,
):
    deck = init_deck(name)
    for d in data:
        deck.add_note(make_note(d, name, str(plies), str(cplies)))
    build_deck_package(deck, board_directory, name, out_directory)
