# Changelog
All notable changes to this project will be documented in this file.

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
