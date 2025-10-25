# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ensure_headless_chromium
Ensure Playwright's Chromium browser is installed and usable.

Strategy:
1. Try to launch Chromium headless via Playwright's Python API.
   - If it works, we're done.
   - If it fails with a "browser not found" style error, try to install.
2. Install attempt prefers `uv run playwright install chromium`,
   then falls back to `sys.executable -m playwright install chromium`.

Intended to be called from other xgid2anki modules;
logging is configured in the main CLI.
"""

import logging
import platform
import shutil
import subprocess
import sys
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def _can_launch_chromium() -> bool:
    """
    Return True if Playwright can launch Chromium headlessly right now.
    Return False if Chromium isn't installed / not available.
    Raise RuntimeError if Playwright itself isn't importable.
    """
    try:
        with sync_playwright() as p:
            # Try to launch Chromium and immediately close it.
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        # Most common failure here (and the one we care about) is that the
        # Chromium executable isn't downloaded yet. In that case we return False.
        logger.debug("Chromium launch check failed: %r", e)
        return False


def ensure_headless_chromium() -> None:
    """
    Ensure Playwright's Chromium browser is installed and usable.
    If not available, attempt to install it automatically.
    """

    # Step 1: if we can already launch Chromium, we're done.
    if _can_launch_chromium():
        logger.info("Playwright Chromium is installed.")
        return

    logger.info("Chromium not found; attempting to install (one-time)…")

    # Step 2: Attempt to install chromium
    py_args = [
        sys.executable,
        "-m",
        "playwright",
        "install",
        "chromium-headless-shell",
    ]
    if platform.system() == "Linux":
        py_args.append("--with-deps")

    try:
        subprocess.run(py_args, check=True)
        # Re-check after install
        if _can_launch_chromium():
            logger.info("Chromium is available for Playwright.")
            return
        else:
            logger.debug(
                "playwright install via current interpreter ran, "
                "but Chromium still not launchable."
            )
    except FileNotFoundError:
        logger.debug(
            "Current interpreter could not run 'python -m playwright'. "
            "Playwright may not be installed in this environment."
        )
    except subprocess.CalledProcessError as e:
        logger.debug("Chromium install via current interpreter failed: %r", e)

    # Step 4: If we got here, we tried installs and Chromium is still not usable.
    logger.error(
        "Failed to install a working Chromium for Playwright.\n"
        "Make sure you have an internet connection."
    )

    manual_msg = (
        "Please run one of the following manually, then rerun xgid2anki:\n\n"
        "    uv tool run --from xgid2anki playwright install --with-deps chromium-headless-shell\n"
    )

    manual_msg += f"or:\n\n    {sys.executable} -m playwright install --with-deps chromium-headless-shell\n"

    logger.info(manual_msg)

    raise ChromiumSetupError("Unable to install or launch Playwright Chromium.")
