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

    # Create a unidirectional pipe: GNUBG (child) writes JSON to *w_fd*;
    # we (parent) read it from *r_fd*.
    r_fd, w_fd = os.pipe()  # create pipe: parent reads r_fd, child writes w_fd

    indices = [i for (i, _) in indexed_batch]
    xgids = [x for (_, x) in indexed_batch]

    # Build env for the child process (GNUBG)
    env = os.environ.copy()
    env["XGIDS"] = json.dumps(xgids)
    env["JSON_FD"] = str(w_fd)
    env["PLIES"] = str(ply)
    env["CUBE_PLIES"] = str(cply)

    # Get path of gnubg script
    gnubg_script = Path(__file__).parent / "gnubg_pos_analysis.py"

    gnubg_args = ["gnubg", "-t", "-q", "-p", gnubg_script]

    # Run script inside gnubg
    p = subprocess.Popen(
        gnubg_args,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        pass_fds=(w_fd,),
        bufsize=1,
        text=True,
    )
    # Close opened pipe
    os.close(w_fd)

    # Read the JSON from the pipe our child writes to.
    with os.fdopen(r_fd, "r") as rfile:
        json_text = rfile.read()

    analysis = json.loads(json_text)

    out, err = p.communicate()
    return p.returncode, analysis, out, err, indices, xgids


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
            rcode, analysis, out, err, indices, xgids_batch = fut.result()
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
