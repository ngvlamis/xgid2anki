# Changelog
All notable changes to this project will be documented in this file.

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
