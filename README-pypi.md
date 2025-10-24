# 🧩 xgid2anki
Convert a list of backgammon XGIDs into an interactive Anki study deck.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-≥3.10-blue.svg)]()
[![PyPI](https://img.shields.io/pypi/v/xgid2anki.svg)](https://pypi.org/project/xgid2anki/)

---

`xgid2anki` is a command-line tool that converts a list of **backgammon positions (XGIDs)** into an **Anki** deck for **spaced-repetition study** using the [Anki flashcard software](https://apps.ankiweb.net).  
Each card includes a rendered board diagram, cube or move decision, and evaluation data extracted from **GNU Backgammon**. 

---

## 📑 Table of Contents
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Command-Line Reference](#-command-line-reference)
- [Configuration](#-configuration)
- [Custom Board Themes](#-custom-board-themes)
- [First-Run Download](#-first-run-download)
- [Known Limitations](#-known-limitations)
- [License](#-license)
- [Example Screenshots](#%EF%B8%8F-example-screenshots)
- [Acknowledgments](#-acknowledgments)

---

## 🚀 Features

- **Analyzes positions** using [GNU Backgammon](https://www.gnu.org/software/gnubg/)  
- **Renders boards** with [bglog](https://nt.bglog.org/NT.html) and headless Chromium  
- **Generates** ready-to-import `.apkg` Anki decks with interactive note templates  
- **Supports multiple card types:**
  - Cube decisions (Double / No Double and Take / Pass)
  - Checker plays (Move decisions)
- **Customizable board themes** — create and save your own theme files using [bglog](https://nt.bglog.org/NT.html)
- **Light and dark themes** automatically match system theme or user-configured preference
- **Configurable** via YAML file or CLI flags  
- **Cross-platform:** macOS, Linux, Windows  
- **Designed for both desktop and mobile Anki clients**

---

## 📦 Installation

You need **Python ≥ 3.10**, **GNU Backgammon**, and a working **Playwright (headless) Chromium browser** install.


> ⚙️ **Required dependency:**  
> `xgid2anki` calls **GNU Backgammon (gnubg)** to analyze positions and extract evaluation data.  
> Make sure `gnubg` is installed and available on your system `PATH`.

#### Installing GNU Backgammon

- **macOS:**  

  The recommended method is via **MacPorts**:
  ```bash
  sudo port install gnubg
  ```

- **Linux (Debian/Ubuntu):**

  ```bash
  sudo apt install gnubg
  ```

- **Windows:**

  Download and install the latest build from [https://www.gnu.org/software/gnubg/#TOCdownloading](https://www.gnu.org/software/gnubg/).

> 💡 **Tip**
>
> You can verify your installation by running:
> `gnubg --version`
> You should see the version number printed without errors.


---

### Installing xgid2anki

`xgid2anki` can be installed using any Python package manager that works with [PyPI](https://pypi.org). 
Both Options 1 and 2 below automatically manage virtual environments and install `xgid2anki` in your system `PATH`.

#### Option 1 – Using [uv](https://docs.astral.sh/uv/) *(recommended)*

`uv` automatically creates an isolated environment and installs Python if necessary.

```bash
# If you don't have uv yet:
# macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# macOS (Homebrew): brew install uv
# Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install xgid2anki
xgid2anki --help
```

#### Option 2 – Using [pipx](https://pypa.github.io/pipx/)

```bash
# If you don't have pipx yet:
# macOS (Homebrew): brew install pipx && pipx ensurepath
# Linux (pip): python -m pip install --user pipx && python -m pipx ensurepath
# Windows (PowerShell): python -m pip install --user pipx && python -m pipx ensurepath
# then restart your shell

pipx install xgid2anki
xgid2anki --help
```
> 📝 **Note**
>
> `pipx` installs `xgid2anki` in its own isolated virtual environment
> and places only the command itself on your `PATH`.


#### Option 3 – Using pip (global or venv)

```bash
python -m pip install --upgrade pip
pip install xgid2anki
xgid2anki --help
```
> ⚠️ **Warning**
>
> Installing with `pip` uses the current environment.
> Prefer `pipx` or `uv` for isolation and easier upgrades.


#### Option 4 – From source

```bash
# Choose a directory where the source should live:
git clone https://github.com/ngvlamis/xgid2anki.git
cd xgid2anki
uv sync  # or: pip install -e .
```

---

### One-time setup for headless Chromium

xgid2anki will automatically install the Playwright headless browser on first run.
If you prefer, you can install it manually:

```bash
# Install Chromium with all required dependencies:
uv run playwright install --with-deps chromium-headless-shell

# or (if installed via pipx):
pipx run playwright install --with-deps chromium-headless-shell

# or (if installed via pip):
playwright install --with-deps chromium-headless-shell
```

---

## 🧠 Quick Start

Create a text file `positions.txt` with one XGID per line:

```
XGID=-b----E-C---eE---c-e----B-:0:0:1:21:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:31:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:41:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:51:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:61:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:32:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:42:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:52:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:62:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:43:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:53:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:63:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:54:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:64:0:0:0:7:10
XGID=-b----E-C---eE---c-e----B-:0:0:1:65:0:0:0:7:10
```

Then run:
```bash
xgid2anki -i positions.txt -d "Opening Moves"
```

This will:
- Analyze each position
- Render each board  
- Generate a deck `Opening Moves.apkg`  
- Print progress and warnings to the console  

Import the resulting `.apkg` into [Anki](https://apps.ankiweb.net) and start studying.

> 📝 **Note**
>
> The example file used above — along with another sample XGID list and their generated Anki decks — can be found in [**docs/examples/**](https://github.com/ngvlamis/xgid2anki/tree/main/docs/examples).  


---

## 🧩 Command-Line Reference

```
xgid2anki [-h] [-i [PATH_OR_XGID ...]] [-o OUTPUT] [-d DECK_NAME]
          [-p {0,1,2,3,4}] [--cube-plies {0,1,2,3,4}]
          [-b {cw,ccw}] [-t THEME] [-c CORES] [-k] [-q]

Generate Anki decks for backgammon positions from XGIDs.
Provide one or more XGIDs or one or more files (one XGID per line).

Options:
  -h, --help             Show this help message and exit.
  --config               Path to a YAML file with defaults (keys must match CLI flags)

Input / Output:
  -i, --input [PATH_OR_XGID ...]
                         Optional. One or more file paths (each containing XGIDs)
                         and/or literal XGIDs. If omitted, xgid2anki will prompt
                         you to select a file or paste XGIDs.
  -o, --output OUTPUT    Output directory or .apkg file
                         (default: current working directory)

Deck & Analysis Options:
  -d, --deck-name DECK_NAME
                         Name for the output Anki deck (required;
                         will prompt if omitted)
  -p, --plies {0,1,2,3,4}
                         Number of plies for checker-play analysis
                         (0–4, default: 3)
  --cube-plies {0,1,2,3,4}
                         Number of plies for cube analysis
                         (0–4, defaults to --plies)
  -b, --bear-off {cw,ccw}
                         Bear-off direction (cw or ccw, default: cw).
  -t, --theme THEME      Path to a custom bglog board theme (JSON).
                         You can design one at https://nt.bglog.org/NT.html.
  -c, --cores CORES      Number of worker processes
                         (default: system CPU count - 1)
  -k, --keep_svg         Keep intermediate SVGs generated during deck creation
  -q, --quiet            Reduce verbosity
```

---

## ⚙️ Configuration

You can define default values in a YAML config file whose keys correspond to the CLI flag names.

```yaml
# config.yaml
deck_name: My Study Deck
plies: 3
cube-plies: 2
theme: ~/themes/my_theme.json
input:
  - ~/xgids/my_deck.txt
  - XGID=-b----E-C---eE---c-e----B-:0:0:1:65:0:0:0:7:10

```
Then run:

```bash
xgid2anki --config config.yaml --cube-plies 3
```

> 💡 **Tip**
>
> YAML keys use the same names as the long-form flags (e.g., cube-plies, deck-name, etc.).
> Any flag that appears on the command line takes precedence over the YAML defaults.


## 🖌️ Custom Board Themes

`xgid2anki` uses [**bglog**](https://nt.bglog.org/NT.html) to render backgammon boards.

You can create your own visual theme directly on the [bglog website](https://nt.bglog.org/NT.html):

1. Open the [bglog website](https://nt.bglog.org/NT.html).
2. Use the menu on the right-hand side to adjust board colors, checker styles, background, and other visual effects.  
3. When you're happy with the design:
   - Click **Themes** in the menu.
   - Click the 💾 **floppy-disk** icon (it appears once you’ve made changes).
   - Then click the 📋 **clipboard** icon to copy the theme JSON to your system clipboard.
   - Paste the contents into a new file (e.g., `my_custom_theme.json`) and save it locally.
4. Use your saved theme in `xgid2anki` via either a CLI flag or YAML config:

   ```bash
   xgid2anki positions.txt --theme my_custom_theme.json
   ```

   or in your YAML config file, add:

   ```yaml
   theme: my_custom_theme.json
   ```

---

## 🌐 First-Run Download

On first launch, `xgid2anki` automatically downloads a local copy of `index.js` from [bglog](https://nt.bglog.org/NT.html) — the JavaScript library used to draw backgammon boards.
**A network connection is required only once.**  
The file is then cached locally (via `platformdirs`) for offline use in later runs.  

---

## ⚠️ Known Limitations

- Currently, no option to use analysis from commercial backgammon software, e.g., [eXtreme Gammon](https://www.extremegammon.com) or [BGBlitz](https://www.bgblitz.com). 
- Requires **Playwright** to render boards. 
- Limited testing on **Android** (AnkiDroid). Decks should import and function normally, but visual rendering and performance may vary.
- 📱 **Mobile / Tablet Layouts:** Deck templates are tuned for portrait mode.  
  Landscape orientation is supported but may render elements (e.g., board images or side-by-side text) inconsistently across devices.

---

## 📜 License

Distributed under the **GNU General Public License v3.0 or later**.  
See the [LICENSE](https://github.com/ngvlamis/xgid2anki/blob/main/LICENSE) file for details.

```
SPDX-License-Identifier: GPL-3.0-or-later
```

---

## 🖼️ Example Screenshots

<p align="center">
  <!-- Row 1 -->
  <a href="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img1.png" title="cube decision — front">
    <img src="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img1.png" width="45%" alt="Cube decision card (front)" />
  </a>
  <a href="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img2.png" title="Cube decision — front">
    <img src="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img2.png" width="45%" alt="Cube decision card (front)" />
  </a>
  <br>
  <a href="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img3.png" title="Cube decision — front">
    <img src="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img3.png" width="45%" alt="Cube decision card (front)" />
  </a>
  <a href="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img5.png" title="Cube decision — front">
    <img src="https://raw.githubusercontent.com/ngvlamis/xgid2anki/main/docs/media/img5.png" width="45%" alt="Cube decision card (front)" />
  </a>
</p>

<p align="center">
  <em>Click any image to view full size.</em>
</p>

> 📝 **Note**
>
> More screenshots (e.g., dark mode, mobile) can be found in [docs/media](https://github.com/ngvlamis/xgid2anki/tree/main/docs/media).


---

## 🙏 Acknowledgments

- [GNU Backgammon](https://www.gnu.org/software/gnubg/) for analysis of positions 
- [bglog](https://nt.bglog.org/NT.html) for backgammon board rendering  
- [Playwright](https://playwright.dev/python/) for headless browser automation  
- [genanki](https://github.com/kerrickstaley/genanki) for Anki deck generation  
- [OpenAI GPT-5](https://openai.com/) for coding and documentation assistance under the author’s direction 

---

### 💬 Feedback

Bug reports and feature suggestions are welcome on the  
[GitHub Issues page](https://github.com/ngvlamis/xgid2anki/issues).

---
