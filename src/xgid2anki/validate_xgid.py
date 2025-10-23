# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.validate_xgid

Utilities to validate an XGID string and enumerate *why* it is invalid.

Design notes
- Pure validation: this module should *not* log by itself; instead it should
  return a normalized XGID (if possible) and a list of human-readable error
  messages that the caller (e.g., CLI) can log or display.
- Error reporting: each check appends a specific string to `errors`, allowing
  the caller to present a detailed report (possibly grouped by field).
- Normalization: if the validator performs any normalization (e.g., stripping
  whitespace, upper/lower conversions), return the normalized XGID alongside
  the error list so the caller can use a canonical form.
"""

from typing import Tuple, List


def is_valid_checker_distribution(s: str) -> bool:
    lower_sum = 0
    upper_sum = 0
    for ch in s:
        if "a" <= ch <= "o":
            lower_sum += ord(ch) - ord("a") + 1
        elif "A" <= ch <= "O":
            upper_sum += ord(ch) - ord("A") + 1
        # early exit if either side exceeds 15
        if lower_sum > 15 or upper_sum > 15:
            return False
    return True  # ≤ 15 each side


def is_nonnegative_int(s: str) -> bool:
    try:
        return int(s) >= 0
    except ValueError:
        return False


def validate_xgid(xgid: str) -> Tuple[str, List[str]]:
    errors: List[str] = []

    # --- normalize prefix and split ---
    head, sep, tail = xgid.partition("=")
    if head == "XGID" and sep:  # 'XGID=...'
        body = tail
        xgid_norm = xgid
    else:
        # No 'XGID=' prefix; assume whole string is the body
        body = xgid
        xgid_norm = "XGID=" + body

    parts = body.split(":")
    if len(parts) != 10:
        errors.append("XGID has wrong number of fields.")
        return xgid_norm, errors

    # Field 1 (position string)
    pos = parts[0]
    if not all(ch == "-" or ("a" <= ch.lower() <= "o") for ch in pos):
        errors.append("Invalid character in position (Field 1).")
    if not is_valid_checker_distribution(pos):
        errors.append("Too many checkers on the board (Field 1).")

    # Field 2 (cube value: nonnegative int)
    if not is_nonnegative_int(parts[1]):
        errors.append("Invalid cube value (Field 2).")

    # Field 3 (cube owner: -1,0,1)
    if parts[2] not in {"-1", "0", "1"}:
        errors.append("Invalid cube position (Field 3).")

    # Field 4 (turn: -1 or 1)
    if parts[3] not in {"-1", "1"}:
        errors.append("Invalid turn numbering (Field 4).")

    # Field 5 (cube/roll: '', {D,B,R}, or two digits)
    p5 = parts[4]
    invalid_p5 = (
        not p5
        or len(p5) > 2
        or (len(p5) == 1 and p5 not in {"D", "B", "R"})
        or (len(p5) == 2 and not all(is_nonnegative_int(d) for d in p5))
    )
    if invalid_p5:
        errors.append("Invalid cube/roll data (Field 5).")
    elif len(p5) == 2 and p5 != "00":
        # must be two digits here
        a, b = map(int, p5)
        if not (1 <= a <= 6 and 1 <= b <= 6):
            errors.append("Invalid dice numbers (Field 5).")

    # Fields 6–7 (scores)
    s_us, s_them = parts[5], parts[6]
    scores_ok = all(is_nonnegative_int(x) for x in (s_us, s_them))

    # Field 9 (match length)
    ml_raw = parts[8]
    ml: int | None
    if is_nonnegative_int(ml_raw):
        ml = int(ml_raw)
    else:
        ml = None
        errors.append("Invalid match length (Field 9).")

    if scores_ok and ml is not None:
        su, st = int(s_us), int(s_them)
        if ml > 0:
            # standard constraint: 0 <= score < match_length
            if not (0 <= su < ml and 0 <= st < ml):
                errors.append("Invalid match score (Field 6/7).")
    elif not scores_ok:
        errors.append("Invalid match score (Field 6/7).")

    # Field 8 (Crawford/Jacoby depending on match type)
    if ml is not None:
        if ml == 0:
            if parts[7] not in {"0", "1", "2", "3"}:
                errors.append("Invalid Jacoby rule settings (Field 8).")
        else:
            if parts[7] not in {"0", "1"}:
                errors.append("Invalid Crawford setting (Field 8).")
            elif parts[7] == "1" and scores_ok and max(su, st) != ml - 1:
                errors.append("Ivalid match score for Crawford setting (Field 8).")

    # Field 10 (max cube)
    if not is_nonnegative_int(parts[9]):
        errors.append("Invalid max cube setting (Field 10).")

    # Doubling action consistency
    # It flags if a doubling action is present but neither side is in a state that could legally double.
    if p5 in {"B", "D", "R"}:
        cond_a = parts[2] == "1" and parts[3] == "-1"  # owner + turn combo A
        cond_b = parts[2] == "-1" and parts[3] == "1"  # owner + turn combo B
        if cond_a or cond_b:
            errors.append("Invalid doubling action: player cannot double (Field 5).")

    return xgid_norm, errors
