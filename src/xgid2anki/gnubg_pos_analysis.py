# ruff: noqa
# xgid2anki - Convert a set of backgammon XGIDs into an Anki study deck
# Copyright (c) 2025 Nicholas G. Vlamis
# SPDX-License-Identifier: GPL-3.0-or-later
"""xgid2anki.gnubg_pos_analysis 

Runs **inside GNUBG** via::

    XGIDS='[\"...\"]' PLIES=3 CUBE_PLIES=3 RESULT_JSON_PATH='C:\\Temp\\gnubg_result_abc123.json' \\
+        gnubg -t -q -p gnubg_pos_analysis.py

--------
Input (env):
- ``XGIDS``: JSON array of XGID strings.
- ``PLIES``: integer search depth for moves (default: 3).
- ``CUBE_PLIES``: integer search depth for cube (default: 3).
- ``RESULT_JSON_PATH``: path to a writable file where this script will dump
  one JSON array of analysis objects.

Output:
- A single JSON document is written to RESULT_JSON_PATH.
  Nothing is guaranteed about stdout/stderr; they may contain GNUBG chatter.
"""

import os, sys, tempfile, json, platform
from contextlib import contextmanager
import gnubg  # REQUIRED when running under 'gnubg'
try:
    from StringIO import StringIO  # Py2
except ImportError:
    from io import StringIO        # Py3


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
    sys.stdin = StringIO("no\n")
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
        data = buff.read()
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return data


def print_to_tty(msg):
    """
    Best-effort progress message for humans ("Analyzing ...").
    On Unix: try /dev/tty first (so we bypass suppressed/redirected fds).
    On Windows (or if /dev/tty fails): fall back to real stdout if possible.

    Nothing here is parsed by the parent process.
    """
    # Make sure we always end with a newline
    line = msg if msg.endswith("\n") else (msg + "\n")

    system = platform.system().lower()

    if system != "windows":
        # Try to write directly to the controlling terminal on POSIX.
        try:
            tty = open("/dev/tty", "w")
            try:
                tty.write(line)
                tty.flush()
                return
            finally:
                tty.close()
        except Exception:
            # If /dev/tty doesn't exist or isn't writable, fall through below.
            pass

    # Fallback: try the interpreter's "real" stdout first (__stdout__),
    # then the possibly reassigned sys.stdout.
    for stream in (getattr(sys, "__stdout__", None), getattr(sys, "stdout", None)):
        if stream:
            try:
                stream.write(line)
                stream.flush()
                return
            except Exception:
                pass

    # Last resort: do nothing. Failing to print progress should not kill analysis.
    return
    

def write_result_json(result_obj):
    """
    Dump result_obj (JSON-serializable) to RESULT_JSON_PATH.
    Exit with a nonzero code if RESULT_JSON_PATH is missing or unwritable.
    """
    out_path = os.environ.get("RESULT_JSON_PATH")
    if not out_path:
        # Hard failure: the parent promised us this.
        sys.stderr.write("gnubg_pos_analysis: RESULT_JSON_PATH not set\n")
        sys.stderr.flush()
        sys.exit(1)

    try:
        with open(out_path, "w") as fp:
            json.dump(result_obj, fp)
    except Exception as e:
        sys.stderr.write("gnubg_pos_analysis: failed to write JSON: %s\n" % e)
        sys.stderr.flush()
        sys.exit(1)


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
        # First start with a warm-up / burn out, which is required for Windows
        capture_output(lambda: gnubg.command("hint"))
        hint_txt = capture_output(lambda: gnubg.command("hint"))
        eval_txt = capture_output(lambda: gnubg.command("eval"))

        output.append({"xgid": xgid, "hint": hint_txt, "eval": eval_txt})

    # Write the full batch result for the parent process to consume
    write_result_json(output)
    # After this point, gnubg will exit and the parent will read+delete the file.
