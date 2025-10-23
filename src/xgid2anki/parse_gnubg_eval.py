# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.parse_gnubg_eval
--------------------------

Parse and normalize GNUBG evaluation output into structured Python data.

This module reads the JSON objects emitted by the GNUBG-side script
(:mod:`xgid2anki.gnubg_pos_analysis`) and extracts the key information
needed to build flashcards—typically equities, best moves, cube decisions,
and other metadata relevant for study.

Responsibilities:
  1. Validate and normalize the raw analysis structure from GNUBG.
  2. Convert strings and numeric fields into consistent Python types.
  3. Return a list of dictionaries, one per analyzed XGID.

Intended to be called from :func:`xgid2anki.pipeline.xgid2anki_pipeline`;
it performs no I/O beyond reading the in-memory GNUBG results.
"""

import re


def parse_cube_hint(position, decision_type):
    # Break the evaluation text into its paragraphs
    eval_paragraphs = re.split(r"\n{3,}", position["eval"])

    # Grab the emg values for no double and double/take
    # (these are ordered in the gnubg eval by value)
    decisions = eval_paragraphs[2].splitlines()
    for j in range(4, 7):
        cube_line = decisions[j].split()
        if cube_line[1] == "No":
            nd = float(cube_line[3])
        elif cube_line[2] == "take":
            dt = float(cube_line[3])

    # Next, we parse the evaluation, obtaining
    # player win chances, player gammon chances, player backgammon chances,
    # opponent gammon chances, opponent backgammon chances, equity, cubeful equity
    lines = eval_paragraphs[1].splitlines()
    eval_line = [line for line in lines if line.strip()][-1].split()[2:]

    # Determine if player is deciding to double or has been doubled and is
    # deciding to take or pass
    if decision_type == "00":
        entry = {
            "xgid": position["xgid"],
            "action": "cube",
            "eval": [float(x) for x in (eval_line[:-2] + eval_line[-1:])],
            "nd_emg": nd,
            "dt_emg": dt,
        }
    else:
        # gnubg's eval gives the doubler's chances of winning and equity rather than
        # the player deciding to take or pass; this converts to the decider's perspective
        eval = []
        eval.append(
            round(1 - float(eval_line[0]), 3)
        )  # Keep to at most three decimal places
        eval.extend(float(x) for x in eval_line[3:5])
        eval.extend(float(x) for x in eval_line[1:3])
        eval.append(float(eval_line[-1]))

        entry = {
            "xgid": position["xgid"],
            "action": "takepass",
            "eval": eval,
            "dt_emg": -dt,
        }

    return entry


def parse_move_hint(position):
    # First we parse the hint for move analysis,
    # recording the move and its score
    hint = position["hint"]
    moves = []

    # Record up to the first six suggested moves
    for idx, line in enumerate(hint.splitlines()[0::3][:6]):
        if idx == 0:
            split = [p for p in re.split(r"\s+|Eq\.:", line) if p][3:]
        else:
            split = [p for p in re.split(r"\s+|Eq\.:", line) if p][3:-1]

        moves.append({"move": split[:-1], "emg": float(split[-1])})

    # Next, we parse the evaluation, obtaining
    # player win chances, player gammon chances, player backgammon chances,
    # opponent gammon chances, opponent backgammon chances, equity, cubeful equity

    lines = re.split(r"\n{3,}", position["eval"])[1].splitlines()
    eval = [line for line in lines if line.strip()][-1].split()[2:]

    return {
        "xgid": position["xgid"],
        "action": "move",
        "moves": moves,
        "eval": [float(x) for x in (eval[:-2] + eval[-1:])],
    }


def parse_gnubg_eval(position_data):
    positions = []

    for pos in position_data:
        move_type = pos["xgid"].split(":")[4]

        if move_type in ["00", "D", "B", "R"]:  # if cube decision
            positions.append(parse_cube_hint(pos, move_type))
        else:  # if move decision
            positions.append(parse_move_hint(pos))

    return positions
