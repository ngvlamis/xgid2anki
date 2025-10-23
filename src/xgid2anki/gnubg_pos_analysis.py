# ruff: noqa
# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.gnubg_pos_analysis (Python 2)

Runs **inside GNUBG** via::

    XGIDS='["..."]' JSON_FD=3 PLIES=3 CUBE_PLIES=3 gnubg -t -q -p gnubg_pos_analysis.py

--------
Input (env):
- ``XGIDS``: JSON array of XGID strings.
- ``PLIES``: integer search depth for moves (default: 3).
- ``CUBE_PLIES``: integer search depth for cube (default: 3).
- ``JSON_FD``: numeric file descriptor; if provided, the script writes a single
  JSON payload to this FD. Otherwise, it writes to stdout.

Output (single JSON document)
"""

import os, sys, tempfile, StringIO, json
from contextlib import contextmanager
import gnubg  # REQUIRED when running under 'gnubg'


@contextmanager
def suppress_fds():
    """Silence all output to stdout/stderr at the OS fd level."""
    old_out_fd = os.dup(1)
    old_err_fd = os.dup(2)
    devnull = open(os.devnull, "w")
    try:
        os.dup2(devnull.fileno(), 1)
        os.dup2(devnull.fileno(), 2)
        yield
    finally:
        os.dup2(old_out_fd, 1)
        os.dup2(old_err_fd, 2)
        os.close(old_out_fd)
        os.close(old_err_fd)
        devnull.close()


@contextmanager
def capture_fds():
    """
    Capture all output sent to stdout/stderr at the OS fd level.
    Yields a temp file; caller must read before the context exits.
    """
    old_out_fd = os.dup(1)
    old_err_fd = os.dup(2)
    tmp = tempfile.TemporaryFile()
    try:
        os.dup2(tmp.fileno(), 1)
        os.dup2(tmp.fileno(), 2)
        yield tmp
    finally:
        os.dup2(old_out_fd, 1)
        os.dup2(old_err_fd, 2)
        os.close(old_out_fd)
        os.close(old_err_fd)
        tmp.close()


def run_with_no(func):
    """Run func once, answering 'no' if prompted; discard all output."""
    old_in = sys.stdin
    sys.stdin = StringIO.StringIO("no\n")
    try:
        with suppress_fds():
            return func()
    finally:
        sys.stdin = old_in


def capture_output(func):
    """Run func once, capturing all stdout/stderr; return captured text."""
    with capture_fds() as buff:
        func()
        buff.flush()
        buff.seek(0)
        return buff.read()


def print_to_tty(msg):
    line = msg if msg.endswith("\n") else (msg + "\n")
    try:
        tty = open("/dev/tty", "w")
        try:
            tty.write(line)
            tty.flush()
        finally:
            tty.close()
    except Exception:
        # Fallback if no TTY
        sys.stdout.write(line)
        sys.stdout.flush()


if __name__ == "__main__":
    # Load inputs
    xgids = json.loads(os.environ["XGIDS"])
    ply = os.environ["PLIES"]
    cply = os.environ["CUBE_PLIES"]
    output = []

    # Configure 3-ply, silently
    with suppress_fds():
        gnubg.command("set evaluation chequerplay evaluation plies " + ply)
        gnubg.command("set evaluation cube evaluation plies " + cply)
        gnubg.command("set evaluation movefilter 3 0 -1 0 0")
        gnubg.command("set evaluation movefilter 3 1 -1 0 0")
        gnubg.command("set evaluation movefilter 3 2 6 0 0")

    for xgid in xgids:
        print_to_tty('Analyzing "{}"...'.format(xgid))

        # Set position; if prompted to swap, auto-answer "no" and suppress chatter
        run_with_no(lambda: gnubg.command("set xgid %s" % xgid))

        # Capture hint/eval (both stdout & stderr from gnubg during the call)
        hint_txt = capture_output(lambda: gnubg.command("hint"))
        eval_txt = capture_output(lambda: gnubg.command("eval"))

        output.append({"xgid": xgid, "hint": hint_txt, "eval": eval_txt})

    # Emit JSON to the dedicated FD if provided; else stdout
    json_text = json.dumps(output)
    json_fd_env = os.environ.get("JSON_FD")
    if json_fd_env:
        try:
            fd = int(json_fd_env)
            w = os.fdopen(fd, "w")
            w.write(json_text)
            w.flush()
            w.close()
        except Exception:
            # Fallback to stdout if FD write fails
            sys.stdout.write(json_text + "\n")
            sys.stdout.flush()
    else:
        sys.stdout.write(json_text + "\n")
        sys.stdout.flush()
