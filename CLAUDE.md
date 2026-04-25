# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up environment
uv sync

# Run the CLI (development)
uv run xgid2anki -i positions.txt -d "My Deck"

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Build the package
uv build

# Publish to PyPI (requires credentials)
uv publish

# Publish to TestPyPI
uv publish --index testpypi
```

There is no test suite currently. Manual testing is done by running the CLI against a sample XGID file (see `docs/examples/`).

## Architecture

`xgid2anki` converts backgammon positions (XGIDs) into importable Anki flashcard decks. The pipeline has five distinct stages orchestrated by `pipeline.py`:

```
CLI (cli.py)
  └─► Pipeline (pipeline.py)
        ├─ 1. Analyze positions  (analyze_positions.py)
        │       └─ spawns gnubg subprocesses in parallel (ProcessPoolExecutor)
        │          each subprocess runs gnubg_pos_analysis.py *inside* gnubg's
        │          embedded Python interpreter, communicating via env vars + temp JSON file
        ├─ 2. Parse gnubg output (parse_gnubg_eval.py)
        │       └─ converts gnubg's text hint/eval output into structured dicts
        ├─ 3. Render boards       (xgid2svg.py)
        │       └─ spins up a local HTTP server + headless Chromium via Playwright
        │          to render SVGs from bglog.js (downloaded once on first run)
        └─ 4. Build Anki deck    (build_deck.py)
                └─ assembles .apkg via genanki using three note models
```

### Key design decisions

**gnubg IPC via temp files**: `gnubg_pos_analysis.py` must be Python 2/3 compatible because it runs inside gnubg's embedded Python. Input arrives via env vars (`XGIDS`, `PLIES`, `CUBE_PLIES`); output is written to a temp file whose path is passed via `RESULT_JSON_PATH`. The parent process reads and deletes the temp file after gnubg exits.

**Card types**: XGID field 5 (index 4 after splitting on `:`) determines the note model:
- `00` → `CubeModel` (player's cube decision)
- `D`, `B`, `R` → `TakePassModel` (opponent offered the cube)
- Any two-digit roll → `MoveModel` (checker play decision)

**Anki model IDs**: Deck and model IDs are derived deterministically via CRC32 in `id_scheme.py` using a stable `VENDOR_NAMESPACE`. When making incompatible changes to note fields or templates in `build_deck.py`, bump `MOVE_MODEL_SCHEMA` or `CUBE_MODEL_SCHEMA` to mint new IDs and avoid collision with previously imported decks.

**Board rendering**: `xgid2svg.py` launches one headless Chromium session per pipeline run (not per board). It serves `bglog.js` over a local HTTP server at port 8877 to satisfy CORS/ES module requirements. Boards are rendered sequentially in the browser; Playwright's `page.evaluate()` is used to load each XGID, optionally draw move arrows, and export SVG via `bglog.toBlob()`.

**bglog.js patching**: On first run, `download_bglog.py` fetches `bglog.js` from the bglog website, applies two string replacements to change away-score display from `−3` to `3A` style, and caches the result in `platformdirs.user_data_dir("xgid2anki")`. The patch is idempotent.

**Move arrow rendering**: For move-type positions, `generate_arrows()` in `pipeline.py` expands each XGID into multiple render tasks — one bare board image plus one per candidate move (with arrows). `sanitize_movelist()` in `xgid2svg.py` breaks compound move notation (e.g., `24/22/20`) into individual segments before passing to bglog's arrow API.

### Module map

| Module | Responsibility |
|---|---|
| `cli.py` | Arg parsing, dependency checks, YAML config loading, XGID collection & validation, entry point |
| `pipeline.py` | End-to-end orchestration |
| `analyze_positions.py` | Parallel gnubg invocation |
| `gnubg_pos_analysis.py` | Runs inside gnubg; performs `hint`/`eval` calls |
| `parse_gnubg_eval.py` | Parses gnubg text output into dicts |
| `xgid2svg.py` | Board SVG rendering via Playwright + bglog.js |
| `build_deck.py` | Anki note/deck construction via genanki |
| `validate_xgid.py` | Pure validation of XGID strings; returns normalized form + error list |
| `download_bglog.py` | Downloads and patches bglog.js; caches in user data dir |
| `id_scheme.py` | Deterministic CRC32-based IDs for Anki decks and models |
| `errors.py` | Custom exceptions: `ConfigError`, `ChromiumSetupError` |
| `templates/` | HTML/CSS Anki card templates (front/back for each card type) |
| `themes/` | Default bglog board theme JSON |

### External dependencies

- **GNU Backgammon (`gnubg`)**: must be on PATH; `gnubg-cli` on Windows
- **Playwright Chromium headless shell**: installed separately via `playwright install chromium-headless-shell`
- **bglog.js**: fetched from `https://nt.bglog.org/bglog/index.js` on first run and cached
