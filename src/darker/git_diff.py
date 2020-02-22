"""Helpers for doing a ``git diff`` and getting modified line numbers

The :func:`git_diff_u0` runs ``git diff -U0 -- <path>``
in the containing directory of ``<path>``,
and returns Git output as a bytestring.

That output can be fed into :func:`get_edit_linenums`
to obtain a list of line numbers in the to-file (modified file)
which were changed from the from-file (file before modification)::

    >>> list(get_edit_linenums(b'''\\
    ... diff --git a/mymodule.py b/mymodule.py
    ... index a57921c..a8afb81 100644
    ... --- a/mymodule.py
    ... +++ b/mymodule.py
    ... @@ -1 +1,2 @@      # will pick +1,2 from this line...
    ... -Old first line
    ... +Replacement for
    ... +first line
    ... @@ -10 +11 @@    # ...and +11 from this line
    ... -Old tenth line
    ... +Replacement for tenth line
    ... '''))
    [1, 2, 11]

"""

import logging
from pathlib import Path
from subprocess import check_output
from typing import Generator, Tuple

logger = logging.getLogger(__name__)


def git_diff(path: Path, context_lines: int) -> bytes:
    """Run ``git diff -U<context_lines> <path>`` and return the output"""
    cmd = ["git", "diff", f"-U{context_lines}", "--", path.name]
    logger.info("[%s]$ %s", path.parent, " ".join(cmd))
    return check_output(cmd, cwd=str(path.parent))


def get_edit_chunks(patch: bytes) -> Generator[Tuple[int, int], None, None]:
    """Yield ranges of changed line numbers in Git diff to-file

    The patch must be in ``git diff -U<num>`` format, and only contain differences for a
    single file.

    Yield 2-tuples of one-based line number ranges which are

    - one-based
    - start inclusive
    - end exclusive

    E.g. ``[42, 7]`` means lines 42, 43, 44, 45, 46, 47 and 48 were changed.

    """
    if not patch:
        return
    git_diff_lines = patch.split(b"\n")
    assert git_diff_lines[0].startswith(b"diff --git ")
    assert git_diff_lines[1].startswith(b"index ")
    assert git_diff_lines[2].startswith(b"--- a/")
    assert git_diff_lines[3].startswith(b"+++ b/")
    for line in git_diff_lines[4:]:
        assert not line.startswith((b"diff --git ", b"index "))
        if not line or line.startswith((b"+", b"-", b" ")):
            continue
        assert line.startswith(b"@@ ")
        start_str, *length_str = line.split()[2].split(b",")
        start_linenum = int(start_str)
        if length_str:
            # e.g. `+42,2` means lines 42 and 43 were edited
            length = int(length_str[0])
        else:
            # e.g. `+42` means only line 42 was edited
            length = 1
        if length:
            # e.g. `+42,0` means lines were deleted starting on line 42 - skip those
            yield start_linenum, start_linenum + length


def get_edit_linenums(patch: bytes) -> Generator[int, None, None]:
    """Yield changed line numbers in Git diff to-file

    The patch must be in ``git diff -U<num>`` format, and only contain differences for a
    single file.

    """
    ranges = list(get_edit_chunks(patch))
    if not ranges:
        logger.info("Found no edited lines")
        return
    logger.info(
        "Found edited line(s) {}".format(
            ", ".join(
                str(start) if end == start + 1 else f"{start}-{end - 1}"
                for start, end in ranges
            )
        )
    )
    for start_linenum, end_linenum in ranges:
        yield from range(start_linenum, end_linenum)
