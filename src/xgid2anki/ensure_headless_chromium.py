# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
ensure_headless_chromium
Ensure Playwright's headless Chromium shell is installed if missing.

Intended to be called from other xgid2anki modules;
logging is configured in the main CLI.
"""

import logging
import platform
import subprocess
import sys

logger = logging.getLogger(__name__)


def ensure_headless_chromium() -> None:
    """Install Playwright's headless Chromium shell if missing."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--list"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout
    except FileNotFoundError:
        logger.error("Playwright does not appear to be installed or is broken.")
        logger.info("You can install it by running: pip install playwright")
        raise

    try:
        if "chromium_headless_shell" not in out:
            args = [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium-headless-shell",
            ]
            if platform.system() == "Linux":
                args.append("--with-deps")
            logger.info("Installing Playwright headless Chromium (one-time)…")
            subprocess.run(args, check=True)
            logger.info("Headless Chromium installed successfully.")
        else:
            logger.info("Playwright headless Chromium found.")
    except subprocess.CalledProcessError:
        logger.error(
            "Failed to install Chromium via Playwright.\n"
            "Make sure you have an internet connection."
        )
