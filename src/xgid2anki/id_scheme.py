# -*- coding: utf-8 -*-
# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.id_scheme
-------------------

Deterministic, human-proof ID scheme for genanki.
- Unlimited decks: stable_deck_id(name) → unique int (same everywhere)
- Versioned models: stable_model_id(name, schema_version="v1")
- Optional override registry if you *ever* need to pin/customize an ID.

This module centralizes all logic for deriving short, unique, and
filesystem-safe IDs for XGIDs, deck elements, and media assets.  Keeping
these conventions in one place ensures reproducibility and prevents naming
collisions when generating or rebuilding decks.

Typical responsibilities:
  1. Generate stable hashes or tokens from XGIDs and related metadata.
  2. Sanitize strings for safe use as filenames and Anki note IDs.
  3. Provide helper functions used by :func:`xgid2anki.pipeline.xgid2anki_pipeline`
     and downstream modules like :mod:`xgid2anki.build_deck`.

Purely functional module — performs no I/O and emits no logging.
"""

from platformdirs import user_data_dir
from pathlib import Path
import json
import zlib

# Application name used for a stable per-user data directory (platformdirs).
APP_NAME = "xgid2anki"
DATA_DIR = data_dir = Path(user_data_dir(APP_NAME))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Keep this string in your repo. Do NOT change lightly.
# Changing it remaps *all* Deck/Model IDs (i.e., new “universe”).
VENDOR_NAMESPACE = "xgid2anki-v1"

# Where manual overrides live (rarely needed)
REGISTRY_PATH = DATA_DIR / ".anki_id_registry.json"


def _crc32_int(s: str) -> int:
    """Positive 31-bit integer from CRC32 (stable across platforms)."""
    return zlib.crc32(s.encode("utf-8")) & 0x7FFFFFFF


def _read_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8") or "{}")
        except Exception:
            return {}
    return {}


def stable_deck_id(deck_name: str, namespace: str = VENDOR_NAMESPACE) -> int:
    """
    Deterministic Deck ID from (namespace, deck_name).
    Same name → same ID. Different names → practically unique IDs.
    """
    reg = _read_registry()
    if "decks" in reg and deck_name in reg["decks"]:
        return int(reg["decks"][deck_name])
    base = f"{namespace}::deck::{deck_name}"
    return _crc32_int(base)


def stable_model_id(
    model_name: str,
    schema_version: str = "v1",
    namespace: str = VENDOR_NAMESPACE,
) -> int:
    """
    Deterministic Model ID from (namespace, model_name@schema_version).
    Bump schema_version when you make incompatible field/template changes.
    """
    reg = _read_registry()
    key = f"{model_name}@{schema_version}"
    if "models" in reg and key in reg["models"]:
        return int(reg["models"][key])
    base = f"{namespace}::model::{key}"
    return _crc32_int(base)


def register_override(kind: str, name: str, new_id: int) -> None:
    """
    Rarely needed. If you *ever* need to force an ID:
      register_override("decks", "Some Deck Name", 1234567890)
      register_override("models", "Model Name@v1", 987654321)
    """
    reg = _read_registry()
    reg.setdefault(kind, {})[name] = int(new_id)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
