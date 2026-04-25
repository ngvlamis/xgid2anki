# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.download_bglog

Responsible for retrieving the upstream `bglog.js` file used by the board renderer
and saving the result into a per-user application data directory determined by
`platformdirs.user_data_dir(APP_NAME)`.

bglog.js is re-downloaded whenever the installed xgid2anki version changes, ensuring
the bundled bglog build stays in sync with each release.

- Raises on network/IO errors; the temp file is cleaned up on failure.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import urllib.request
from importlib.metadata import version as pkg_version
from pathlib import Path

from platformdirs import user_data_dir

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_NAME = "xgid2anki"
_BGLOG_URL = "https://nt.bglog.org/bglog/index.js"
_BGLOG_FILENAME = "bglog.js"
_VERSION_FILENAME = ".bglog_xgid2anki_version"

logger = logging.getLogger(__name__)


def _format_size(nbytes: int) -> str:
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024**2:
        return f"{nbytes / 1024:.2f} KB"
    return f"{nbytes / 1024**2:.2f} MB"


def get_bglog_path() -> Path:
    """Canonical location for bglog.js in the per-user data directory."""
    data_dir = Path(user_data_dir(APP_NAME))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / _BGLOG_FILENAME


def _current_app_version() -> str:
    try:
        return pkg_version(APP_NAME)
    except Exception:
        return "unknown"


def _cached_bglog_version(bglog_path: Path) -> str | None:
    """Return the xgid2anki version that last downloaded bglog.js, or None."""
    version_file = bglog_path.parent / _VERSION_FILENAME
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _write_bglog_version(bglog_path: Path) -> None:
    version_file = bglog_path.parent / _VERSION_FILENAME
    version_file.write_text(_current_app_version(), encoding="utf-8")


def download_bglog(force: bool = False) -> Path:
    """
    Ensure bglog.js exists at the canonical per-user data dir.
    Re-downloads if missing, forced, or if xgid2anki has been updated since
    the last download. Returns the final Path.
    """
    out_path = get_bglog_path()
    app_version = _current_app_version()

    if out_path.exists() and not force:
        cached_version = _cached_bglog_version(out_path)
        if cached_version == app_version:
            logger.info("Found existing bglog.js at %s", out_path)
            return out_path
        elif cached_version is None:
            logger.info("No version marker found for cached bglog.js; re-downloading…")
        else:
            logger.info(
                "xgid2anki updated (%s → %s); re-downloading bglog.js…",
                cached_version,
                app_version,
            )

    logger.info("Downloading bglog.js…")

    tmp_path = out_path.with_suffix(".download")
    try:
        req = urllib.request.Request(
            _BGLOG_URL, headers={"User-Agent": f"xgid2anki/{app_version}"}
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
        _write_bglog_version(out_path)
        logger.info("Saved bglog.js to %s", out_path)
        return out_path

    except Exception as e:
        with contextlib.suppress(Exception):
            if tmp_path.exists():
                tmp_path.unlink()
        logger.error("Failed to download bglog.js: %s", e)
        raise
