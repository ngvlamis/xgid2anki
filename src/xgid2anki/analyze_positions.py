# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.analyze_positions
Analyze backgammon positions with GNU Backgammon (GNUBG).

This module batches XGIDs, invokes GNUBG once per batch (via a Python 2
script that runs inside GNUBG), collects JSON analysis through a pipe, and
returns results in the same order as the input XGIDs.

Intended to be called from :func:`xgid2anki.pipeline.xgid2anki_pipeline`; emits progress via
:mod:`logging` but performs no console I/O.
"""

import os
import json
import subprocess
import platform
import tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def split_into_n(seq, n):
    n = max(1, int(n))
    L = len(seq)
    q, r = divmod(L, n)
    out, i = [], 0
    for k in range(n):
        sz = q + (1 if k < r else 0)
        if sz:
            out.append(seq[i : i + sz])
            i += sz
    return out


def run_gnubg_batch(indexed_batch, ply, cply):
    """Invoke GNUBG once for a batch of XGIDs."""

    indices = [i for (i, _) in indexed_batch]
    xgids = [x for (_, x) in indexed_batch]

    # 1. Create a temporary file path for GNUBG to write machine-readable JSON.
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        prefix="gnubg_result_",
        suffix=".json",
    )
    tmp_path = tmp.name
    tmp.close()  # child (gnubg) will open this path itself

    # 2. Build environment for the child process (GNUBG).
    #    We tell gnubg_pos_analysis.py:
    #      - which XGIDs to analyze
    #      - ply / cube_plies depth settings
    #      - where to write the final JSON bundle
    env = os.environ.copy()
    env["XGIDS"] = json.dumps(xgids)
    env["PLIES"] = str(ply)
    env["CUBE_PLIES"] = str(cply)
    env["RESULT_JSON_PATH"] = tmp_path

    # 3. Work out which gnubg binary to call.
    #    On Windows we expect gnubg-cli.exe / gnubg-cli in PATH.
    #    On Unix-y systems we expect gnubg to be callable.
    system = platform.system().lower()
    if system == "windows":
        gnubg_command = "gnubg-cli"
    else:
        gnubg_command = "gnubg"

    gnubg_script = Path(__file__).parent / "gnubg_pos_analysis.py"
    gnubg_args = [gnubg_command, "-t", "-q", "-p", gnubg_script]

    # 4. Launch GNUBG. We still capture stdout/stderr (merged) to `out`
    #    in case we want to log/debug it, but we DO NOT try to parse it.
    completed = None
    analysis = None
    try:
        completed = subprocess.run(
            gnubg_args,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        #
        # 5. Read the structured analysis that gnubg_pos_analysis.py
        #    should have written to tmp_path as valid JSON.
        #
        with open(tmp_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)

    finally:
        # 6. Cleanup temp file no matter what.
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    # 7. Return the same shape analyze_positions() already expects:
    #    (returncode, analysis_obj, out, indices, xgids_batch)

    out = completed.stdout if completed is not None else ""

    return completed.returncode, analysis, out, indices, xgids


def analyze_positions(xgids, procs=0, plies=3, cube_plies=3):
    """Analyze a collection of XGIDs with GNUBG, using a worker pool."""
    if procs == 0:
        procs = max(1, (os.cpu_count() or 1) - 2)
    procs = min(procs, len(xgids))  # don’t spawn more workers than tasks

    # Keep original order by indexing the xgids
    indexed = list(enumerate(xgids))
    batches = split_into_n(indexed, procs)

    # Prepare result container in original order
    results = [None] * len(xgids)

    rc = 0
    with ProcessPoolExecutor(max_workers=procs) as ex:
        futs = [ex.submit(run_gnubg_batch, b, plies, cube_plies) for b in batches]
        for fut in as_completed(futs):
            rcode, analysis, out, indices, xgids_batch = fut.result()
            if rcode != 0 and rc == 0:
                rc = rcode

            # Merge this batch’s analysis into the right slots
            if isinstance(analysis, list):
                # Assume analysis aligns positionally with xgids_batch
                for idx, a in zip(indices, analysis):
                    results[idx] = a
            elif isinstance(analysis, dict):
                # Assume analysis keyed by XGID
                for idx, x in zip(indices, xgids_batch):
                    results[idx] = analysis.get(x)
            else:
                # Fallback: store raw analysis for the first slot
                for idx in indices:
                    results[idx] = analysis

    return results, rc
