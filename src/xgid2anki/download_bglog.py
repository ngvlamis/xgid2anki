# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.download_bglog

Responsible for retrieving the upstream `bglog.js` file used by the board renderer
and saving the result into a per-user application data directory determined by
`platformdirs.user_data_dir(APP_NAME)`.

- Safe to call multiple times; re-downloads only when needed or force=True.
- If the cached file contains old xgid2anki score-display patches (no longer needed
  since bglog natively supports away-style scores via the scoreStyle theme setting),
  a fresh download is triggered automatically.
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
# Configuration
# ---------------------------------------------------------------------------

APP_NAME = "xgid2anki"
_BGLOG_URL = "https://nt.bglog.org/bglog/index.js"
_BGLOG_FILENAME = "bglog.js"

# Presence of this string indicates an old patched file that should be replaced.
_LEGACY_PATCH_MARKER = "matchLength - this.oppScore)+'A'"

logger = logging.getLogger(__name__)


def _format_size(nbytes: int) -> str:
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024**2:
        return f"{nbytes / 1024:.2f} KB"
    return f"{nbytes / 1024**2:.2f} MB"


def get_bglog_path() -> Path:
    """Canonical location for bglog.js in the per-user data directory."""
    data_dir = Path(
        user_data_dir(APP_NAME)
    )  # e.g. macOS: ~/Library/Application Support/xgid2anki
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / _BGLOG_FILENAME


def _is_legacy_patched(js_text: str) -> bool:
    """Return True if the file contains the old xgid2anki away-score patches."""
    return _LEGACY_PATCH_MARKER in js_text


def download_bglog(force: bool = False) -> Path:
    """
    Ensure bglog.js exists at the canonical per-user data dir.
    Re-downloads if missing, forced, or if the cached file is an old patched version.
    Returns the final Path.
    """
    out_path = get_bglog_path()

    if out_path.exists() and not force:
        try:
            text = out_path.read_text(encoding="utf-8")
            if _is_legacy_patched(text):
                logger.info(
                    "Cached bglog.js contains old score-display patches; "
                    "re-downloading latest version…"
                )
            else:
                logger.info("Found existing bglog.js at %s", out_path)
                return out_path
        except Exception as e:
            logger.warning("Could not read cached bglog.js: %s — re-downloading…", e)

    logger.info("Downloading bglog.js…")

    tmp_path = out_path.with_suffix(".download")
    try:
        req = urllib.request.Request(
            _BGLOG_URL, headers={"User-Agent": "xgid2anki/1.0"}
        )
        with (
            urllib.request.urlopen(req, timeout=30) as resp,
            open(tmp_path, "wb") as fh,
        ):
            shutil.copyfileobj(resp, fh)

        size = tmp_path.stat().st_size
        logger.info("Downloaded bglog.js (%s)", _format_size(size))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_path, out_path)
        logger.info("Saved bglog.js to %s", out_path)
        return out_path

    except Exception as e:
        with contextlib.suppress(Exception):
            if tmp_path.exists():
                tmp_path.unlink()
        logger.error("Failed to download bglog.js: %s", e)
        raise
