# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""
xgid2anki.xgid2svg
------------------

Render backgammon positions (XGIDs) as SVG boards using the bglog JavaScript
renderer.  Each position is converted to an HTML fragment rendered in a
headless Chromium instance and saved as an SVG (or PNG, if configured).

bglog is hosted at https://nt.bglog.org/NT.html

This module acts as a bridge between Python and bglog:
  1. Generate a minimal HTML wrapper around bglog.js.
  2. Launch Playwright’s headless Chromium to render boards off-screen.
  3. Capture and store the resulting SVGs in a designated folder.

Intended to be called from :func:`xgid2anki.pipeline.xgid2anki_pipeline`; emits progress via
:mod:`logging` but performs no console I/O.
"""

import base64
import os
import re
import unicodedata
import threading
import logging
from tqdm import tqdm
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    s = unicodedata.normalize("NFC", str(name)).strip()
    s = s.replace("*", "h")  # encode hits
    s = re.sub(r"[:\\/=]+", "_", s)  # :, \, /, = → _
    s = re.sub(r"\s+", "_", s)  # spaces → _
    s = re.sub(r"_+", "_", s)  # collapse runs
    return s


def sanitize_movelist(movelist):
    moves = movelist.split()
    arrow_list = []
    for move in moves:
        move = move.replace("*", "")
        if move.endswith("(2)"):
            # Break a multiplied chain (eg, 24/22/20(2)) into invidiual multiple moves (eg, 24/22(2) 22/20(2))
            base = move[:-3]
            points = base.split("/")
            arrow_list.extend(
                [f"{points[i]}/{points[i + 1]}(2)" for i in range(len(points) - 1)]
            )

        else:
            points = move.split("/")
            if len(points) > 2:
                # Break a chain of moves (eg, 24/22/20) into individual moves (eg, 24/22 22/20).
                arrow_list.extend(
                    [f"{points[i]}/{points[i + 1]}" for i in range(len(points) - 1)]
                )
            else:
                # If a normal chain, keep as is
                arrow_list.append(move)
    return arrow_list


def start_http_server(directory: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress all logging

    httpd = ThreadingHTTPServer(("127.0.0.1", 8877), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    logger.info("Starting local http server to run bglog …")
    t.start()
    return httpd


def xgid2svg(boards, bglog_path, theme):
    # Ensure bglog_path is a path
    if not isinstance(bglog_path, (str, Path)):
        raise TypeError(
            f"Expected str or Path, got {type(bglog_path).__name__} for path to bglog.js."
        )
    bglog_path = Path(bglog_path) if not isinstance(bglog_path, Path) else bglog_path
    folder = bglog_path.parent

    # Generate temporary html to load js
    html = f"""
        <!doctype html>
        <meta charset="utf-8" />
        <title>bgLog export</title>
        <bg-log id="bglogContainer"></bg-log>
        <script type="module">
            // Load your local module from the same origin
            await import("./{bglog_path.name}");
            await customElements.whenDefined("bg-log");
        </script>
        """
    with open(folder / ".temporary.html", "w") as f:
        f.write(html)

    # Start local server to avoid CORS/module issues
    httpd = start_http_server(folder)

    url = "http://127.0.0.1:8877/.temporary.html"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            logger.info("Opening headless browser to access bglog …")
            ctx = browser.new_context()
            page = ctx.new_page()

            # Visit the temp page
            page.goto(url, wait_until="domcontentloaded")

            # Wait until the element exists *and* the method is available
            page.wait_for_function(
                """
                const el = document.getElementById('bglogContainer');
                el && el.bglog && typeof el.bglog.loadXgId === 'function';
                """
            )

            ## Set the theme
            page.evaluate(
                """(theme) => {
                    const el = document.getElementById("bglogContainer");
                    for (const [key, value] of Object.entries(theme)) {
                        el.bglog.currentTheme[key] = value;
                    }
                    el.bglog.redraw();
                }""",
                theme,
            )

            for board in tqdm(boards, desc="Generating board images"):
                xgid = board[0]

                # Load board position from XGID
                page.evaluate(
                    f"document.getElementById('bglogContainer').bglog.loadXgId('{xgid}')"
                )

                # Check if there are arrows to draw, and if so, draw them
                if len(board) > 1:
                    arrows = " ".join(sanitize_movelist(board[1]))
                    page.evaluate(
                        """async (arrows) => {
                            const el = document.getElementById("bglogContainer");
                            const { moves, error } = el.bglog.parseArrowMove(arrows);
                            el.bglog.setArrows(moves);
                        }""",
                        arrows,
                    )
                else:
                    arrows = None

                # Wait a bit for rendering
                # page.wait_for_timeout(600)

                # Ask the controller for an SVG blob and return it as base64
                b64 = page.evaluate(
                    """async () => {
                        const el = document.getElementById("bglogContainer");
                        if (!el?.bglog?.toBlob) throw new Error("bglog.toBlob() not available");
                        const blob = await el.bglog.toBlob(); // SVG
                        const buf = await blob.arrayBuffer();
                        let bin = '';
                        const bytes = new Uint8Array(buf);
                        for (let i=0; i<bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                        return btoa(bin);
                    }"""
                )

                # Create output folder
                out_dir = folder / "board-images"
                out_dir.mkdir(exist_ok=True)

                svg_bytes = base64.b64decode(b64)
                if arrows:
                    # Build the *same* basename in both places:
                    xgid_part = sanitize_filename(xgid)
                    move_part = sanitize_filename(board[1].replace(" ", "m"))
                    basename = f"{xgid_part}_{move_part}.svg"
                    out_path = out_dir / basename
                    # out_path = out_dir / (sanitize_filename(xgid+'-'+"_".join(arrow_list)) + ".svg")
                else:
                    xgid_part = sanitize_filename(xgid)
                    basename = f"{xgid_part}.svg"
                    out_path = out_dir / basename
                    # out_path = out_dir / (sanitize_filename(xgid) + ".svg")

                # Save svg
                out_path.write_bytes(svg_bytes)

            ctx.close()
            browser.close()
            logger.info("Headless browser closed.")

    finally:
        # Stop server
        httpd.shutdown()
        logger.info("Local http server shutdown.")
        # Delete temp html file
        os.remove(folder / ".temporary.html")
