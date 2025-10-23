# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.download_bglog

Responsible for retrieving the upstream `bglog.js` file used by the board renderer,
optionally patching two away-score display lines (to show e.g. `3A` instead of `-3`),
and saving the result into a per-user application data directory determined by
`platformdirs.user_data_dir(APP_NAME)`.

- Safe to call multiple times; idempotently verifies/patches existing files unless `force=True`.
- Logs progress and warnings (e.g., when expected patch lines are not found upstream).
- Raises on network/IO errors; the temp file is cleaned up on failure.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import urllib.request
from pathlib import Path

from platformdirs import user_data_dir

# ---------------------------------------------------------------------------
# Configuration & patch metadata
# ---------------------------------------------------------------------------

# Application name used for a stable per-user data directory (platformdirs).
APP_NAME = "xgid2anki"
_BGLOG_URL = "https://nt.bglog.org/bglog/index.js"
_BGLOG_FILENAME = "bglog.js"

# Two exact lines expected in upstream bglog.js to be patched.
# If upstream changes, entries may not be found; we warn but continue.
_OLD_LINES = [
    'this.$("#oppScoreText").text("\\u2013" + (this.matchLength - this.oppScore));',
    'this.$("#ourScoreText").text("\\u2013" + (this.matchLength - this.ourScore));',
]
# Replacement lines to render away score like "nA" (e.g., 3A).
_NEW_LINES = [
    "this.$(\"#oppScoreText\").text((this.matchLength - this.oppScore)+'A');",
    "this.$(\"#ourScoreText\").text((this.matchLength - this.ourScore)+'A');",
]

# Module-level logger (configured by caller/CLI).
logger = logging.getLogger(__name__)


def _format_size(nbytes: int) -> str:
    """Human-friendly byte size formatter used for progress logging."""
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024**2:
        return f"{nbytes / 1024:.2f} KB"
    return f"{nbytes / 1024**2:.2f} MB"


def get_bglog_path() -> Path:
    """Canonical location for bglog.js without org name or env overrides."""
    data_dir = Path(
        user_data_dir(APP_NAME)
    )  # e.g. macOS: ~/Library/Application Support/xgid2anki
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / _BGLOG_FILENAME


def _patch_bglog_text(js_text: str) -> tuple[str, list[str]]:
    """Return (patched_text, warnings). No-op if already patched."""
    warnings: list[str] = []
    if all(new in js_text for new in _NEW_LINES):
        return js_text, warnings  # already patched

    patched = js_text
    for old, new in zip(_OLD_LINES, _NEW_LINES):
        if old in patched:
            patched = patched.replace(old, new)
        else:
            warnings.append(f"Expected line not found (skipped): {old}")
    return patched, warnings


def download_bglog(force: bool = False) -> Path:
    """
    Ensure bglog.js exists at the canonical per-user data dir (no org name).
    Downloads and patches if needed. Returns the final Path.
    """
    out_path = get_bglog_path()

    if out_path.exists() and not force:
        logger.info("Found existing bglog.js at %s", out_path)
        # Verify/patch idempotently
        try:
            text = out_path.read_text(encoding="utf-8")
            patched, warns = _patch_bglog_text(text)
            if patched != text:
                tmp = out_path.with_suffix(".tmp")
                tmp.write_text(patched, encoding="utf-8")
                shutil.move(tmp, out_path)
                logger.info("Patched existing bglog.js (away-score style updated)")
            for w in warns:
                logger.warning(w)
        except Exception as e:
            # If verification/patching fails, keep existing file but surface the issue.
            logger.warning("Failed to verify/patch existing bglog.js: %s", e)
        return out_path

    logger.info("No copy of bglog found (or force=True). Downloading bglog now…")

    tmp_path = out_path.with_suffix(".download")
    try:
        req = urllib.request.Request(
            _BGLOG_URL, headers={"User-Agent": "xgid2anki/1.0"}
        )
        # Stream download into a temporary file to avoid partial writes on failure.
        with (
            urllib.request.urlopen(req, timeout=30) as resp,
            open(tmp_path, "wb") as fh,
        ):
            shutil.copyfileobj(resp, fh)

        size = tmp_path.stat().st_size
        logger.info("Downloaded bglog.js (%s)", _format_size(size))

        # Perform patching in-place on the temp file; write back only if changes occur.
        text = tmp_path.read_text(encoding="utf-8")
        patched, warns = _patch_bglog_text(text)
        if patched != text:
            tmp_path.write_text(patched, encoding="utf-8")
            logger.info("Patched bglog.js (away-score style updated)")
        for w in warns:
            logger.warning(w)

        # Ensure destination dir exists and then move into place.
        # shutil.move handles cross-device copies if needed.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_path, out_path)
        logger.info("Saved bglog.js to %s", out_path)
        return out_path

    except Exception as e:
        # Best-effort cleanup of temporary file; don't mask the original error.
        with contextlib.suppress(Exception):
            if tmp_path.exists():
                tmp_path.unlink()
        logger.error("Failed to download bglog.js: %s", e)
        raise
