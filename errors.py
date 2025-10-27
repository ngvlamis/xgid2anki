# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.errors

Custom exception classes used across the xgid2anki package.
"""

class ConfigError(Exception):
    """Raised when there is an error loading or parsing the user files specified in the config."""
    pass


class ChromiumSetupError(RuntimeError):
    """Raised when Playwright's Chromium cannot be installed or launched."""
    pass
