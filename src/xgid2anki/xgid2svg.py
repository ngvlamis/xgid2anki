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
import xml.etree.ElementTree as ET
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


def create_arrow_overlay(base_svg_bytes: bytes, arrow_svg_bytes: bytes) -> bytes:
    """Return an SVG containing only elements added by the arrow render vs the bare board.

    Compares each direct child of the SVG root by serialized form.  Any child
    present in the arrow SVG but absent in the base SVG is included in the
    overlay.  The overlay has the same viewBox/dimensions as the originals but
    no opaque background, so it can be CSS-stacked on top of the base board.

    Falls back to returning the full arrow SVG unchanged if no diff is found
    (e.g. bglog appends arrows inside an existing group rather than as new
    top-level elements).
    """
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)

    try:
        base_root = ET.fromstring(base_svg_bytes)
        arrow_root = ET.fromstring(arrow_svg_bytes)
    except ET.ParseError as exc:
        logger.warning("SVG parse error during overlay diff (%s); using full SVG", exc)
        return arrow_svg_bytes

    base_serialized = {ET.tostring(c) for c in base_root}
    new_elements = [c for c in arrow_root if ET.tostring(c) not in base_serialized]

    if not new_elements:
        logger.debug("SVG diff found no new top-level elements; falling back to full SVG")
        return arrow_svg_bytes

    overlay_root = ET.Element(f"{{{SVG_NS}}}svg")
    for attr, val in arrow_root.attrib.items():
        overlay_root.set(attr, val)
    for elem in new_elements:
        overlay_root.append(elem)

    header = b'<?xml version="1.0" encoding="utf-8"?>\n'
    return header + ET.tostring(overlay_root, encoding="unicode").encode("utf-8")


def start_http_server(directory: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress all logging

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
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
    port = httpd.server_address[1]

    url = f"http://127.0.0.1:{port}/.temporary.html"

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
                    // Remove animation for swapping sides
                    el.bglog.swapSidesDuration=0;
                }""",
                theme,
            )

            # We will always keep player on turn on the bottom
            # Iniatilize with the assumption that the player on turn is on the bottom
            current_orientation = 1

            # Cache bare-board SVG bytes keyed by XGID so arrow variants can be
            # diffed against them to produce small overlay-only SVG files.
            base_svg_cache: dict[str, bytes] = {}

            # Create output folder once before the loop
            out_dir = folder / "board-images"
            out_dir.mkdir(exist_ok=True)

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

                # Make sure player on roll is shown at the bottom of the board
                new_orientation = int(xgid.split(":")[3])

                if new_orientation != current_orientation:
                    current_orientation = new_orientation
                    page.evaluate(
                        """
                        const el = document.getElementById("bglogContainer");
                        // swapSides flips which checkers are top/bottom
                        el.bglog.swapSides();
                        // toggleDirection flips bearoff direction so pips point the right way
                        el.bglog.toggleDirection();
                        // swapColors swaps the colors, so white is on roll
                        el.bglog.swapColors();
                        """
                    )

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

                svg_bytes = base64.b64decode(b64)
                xgid_part = sanitize_filename(xgid)

                if arrows:
                    move_part = sanitize_filename(board[1].replace(" ", "m"))
                    basename = f"{xgid_part}_{move_part}.svg"
                    out_path = out_dir / basename
                    base = base_svg_cache.get(xgid)
                    out_path.write_bytes(
                        create_arrow_overlay(base, svg_bytes) if base else svg_bytes
                    )
                else:
                    basename = f"{xgid_part}.svg"
                    out_path = out_dir / basename
                    out_path.write_bytes(svg_bytes)
                    base_svg_cache[xgid] = svg_bytes

            ctx.close()
            browser.close()
            logger.info("Headless browser closed.")

    finally:
        # Stop server
        httpd.shutdown()
        logger.info("Local http server shutdown.")
        # Delete temp html file
        os.remove(folder / ".temporary.html")
