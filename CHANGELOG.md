# Changelog
All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-12
### Changed
- Move-type cards now store arrow moves as lightweight SVG overlays (~3 elements) rather than full board re-renders (~24 KB each), significantly reducing `.apkg` file size. Card templates use CSS grid stacking to layer the overlay on top of the base board image. Falls back to a full SVG if the diff yields no new elements.

### Fixed
- Arrow overlay SVG was missing `grid-area: 1/1`, causing it to render below the board and obscure the copy button.
- Copy button in `move_back` and `takepass_back` used an async click handler that broke `execCommand("copy")`'s user-gesture requirement in Anki's webview; replaced with a synchronous handler matching `cube_back`.

## [0.1.9] - 2026-04-25
### Changed
- bglog now supports away-style scores natively; removed JS patching from `download_bglog.py` and updated default theme to use `scoreStyle: awayalpha`
- `bglog.js` is now re-downloaded automatically whenever xgid2anki is updated, keeping the bglog build in sync with each release
- `__version__` is now read dynamically from package metadata, keeping `pyproject.toml` as the single source of truth

### Fixed
- Positional arguments (e.g. `xgid2anki positions.txt`) were silently ignored; input is now correctly merged with `-i/--input`
- Hard-coded local HTTP server port 8877 replaced with OS-assigned port to avoid conflicts
- `parse_cube_hint` could raise an uninformative `UnboundLocalError` if gnubg output was unexpected; now raises a clear `ValueError` caught gracefully in the pipeline
- Anki model schema version constants (`MOVE_MODEL_SCHEMA`, `CUBE_MODEL_SCHEMA`) were defined but not used; model IDs are now derived from the correct per-model constants
- Typo in XGID validation error message ("Ivalid" → "Invalid")
- Typo in output path error message ("ouput" → "output")

### Note
- Custom themes using the old `awayStyle` key will need to be updated to use `scoreStyle: awayalpha` (or `away` / `absolute`)

## [0.1.7] - 2025-10-27
### Fixed
- Missing `errors.py` error

## [0.1.7] - 2025-10-27
### Fixed
- Fixed board orientation so the player on roll is always on bottom (auto-flip if XGID shows otherwise)
- Fixed issue where boards did not display on Android devices
- Removed unused `err` variable from `analyze_positions.py`
- Removed unnecessary `import shutil` from `ensure_headless_chromium.py`

### Added
- Added `errors.py` module defining custom exceptions and imported where needed

## [0.1.6] - 2025-10-26
### Fixed
- Corrected a typo in Anki card template text

## [0.1.5] – 2025-10-25
### Added
- Full **Windows compatibility** for GNU Backgammon analysis:  
  - `xgid2anki.analyze_positions` now uses **temporary files** for structured data exchange instead of Unix-only pipes (`pass_fds`).  
  - This enables position analysis and batch processing to run correctly on Windows systems.  
- Automatic detection of the correct GNU Backgammon executable:  
  - Uses `gnubg-cli` on Windows and `gnubg` on Unix-based systems.  
- Graceful fallback behavior for `print_to_tty` inside `gnubg_pos_analysis.py` (silently no-ops on Windows).  

### Changed
- Simplified inter-process communication between `analyze_positions.py` and `gnubg_pos_analysis.py`:  
  - Removed reliance on `JSON_FD` and custom file descriptors.  
  - Replaced with a single cross-platform environment variable `RESULT_JSON_PATH`.  
- Unified the analysis path: macOS, Linux, and Windows now share identical code paths—no OS-specific branching.  
- Updated **README** installation instructions:  
  - Added link to **MacPorts** install instructions.
  - Added detailed Windows to ensure the installation folder for `gnubg-cli.exe` is added to the system **PATH**.  

### Fixed
- **Windows:** eliminated the `OSError: pass_fds not supported on Windows` crash when invoking `gnubg-cli.exe`.  
- **Windows:** ensured correct invocation of `gnubg-cli.exe` instead of the GUI binary (`gnubg.exe`).  
- Ensured temporary result files are safely created and deleted per worker process (thread-safe and parallel-safe).  

## [0.1.4] - 2025-10-24
### Changed
- `cli.py`: added custom exception class for playwright browswer error
- `ensure_headless_chromium`: removed unnecessary checks and an incorrect installation attempt
- Corrected README instructions for installing headless chromium browswer
- Updated REAMDE to include note regarding adding uv to `PATH` variable

## [0.1.3] - 2025-10-24
### Fixed
- Updated PyPI README formatting and image links.

## [0.1.2] - 2025-10-24

### Fixed
- `ensure_headless_chromium`: fixed bug when Playwright was already installed.
- `gnubg_pos_analysis`: fixed compatibility issue with modern GNU Backgammon builds using the built-in Python 3 interpreter.

### Changed
- Updated README installation instructions to exclusively recommend Astral’s **uv**.

## [0.1.1] - 2025-10-23
### Added
- First official release on PyPI.

## [0.1.0] - 2025-10-23
### Added
- Initial release on Test PyPI.
