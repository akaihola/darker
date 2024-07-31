"""Darker GitHub action implementation"""

import os
import shlex
import sys
from pathlib import Path
from subprocess import PIPE, STDOUT, run  # nosec

ACTION_PATH = Path(os.environ["GITHUB_ACTION_PATH"])
ENV_PATH = ACTION_PATH / ".darker-env"
ENV_BIN = ENV_PATH / ("Scripts" if sys.platform == "win32" else "bin")
OPTIONS = os.getenv("INPUT_OPTIONS", default="")
SRC = os.getenv("INPUT_SRC", default="")
VERSION = os.getenv("INPUT_VERSION", default="")
REVISION = os.getenv("INPUT_REVISION") or os.getenv("INPUT_COMMIT_RANGE") or "HEAD^"
WORKING_DIRECTORY = os.getenv("INPUT_WORKING_DIRECTORY", ".")

if os.getenv("INPUT_LINT", default=""):
    print(
        "::notice:: Baseline linting has been moved to the Graylint package."
        " See https://pypi.org/project/graylint for more information.",
    )


def set_github_output(key: str, val: str) -> None:
    """Write a key-value pair to the output file."""
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="UTF-8") as f:
        if "\n" in val:
            print(f"{key}<<DARKER_ACTION_EOF", file=f)
            print(val, file=f, end="" if val.endswith("\n") else "\n")
            print("DARKER_ACTION_EOF", file=f)
        else:
            print(f"{key}={val}", file=f)


def exit_with_exitcode(exitcode: int) -> None:
    """Write the exit code to the output file and exit with it."""
    set_github_output("exitcode", str(exitcode))
    sys.exit(exitcode)


# Check if the working directory exists
if not os.path.isdir(WORKING_DIRECTORY):
    print(f"::error::Working directory does not exist: {WORKING_DIRECTORY}", flush=True)
    exit_with_exitcode(21)


def pip_install(*packages):
    """Install the specified Python packages using a pip subprocess."""
    python = str(ENV_BIN / "python")
    args = [python, "-m", "pip", "install", *packages]
    pip_proc = run(  # nosec
        args,
        check=False,
        stdout=PIPE,
        stderr=STDOUT,
        encoding="utf-8",
    )
    print(pip_proc.stdout, end="")
    if pip_proc.returncode:
        print(f"::error::Failed to install {' '.join(packages)}.", flush=True)
        sys.exit(pip_proc.returncode)


if not ENV_PATH.exists():
    run([sys.executable, "-m", "venv", str(ENV_PATH)], check=True)  # nosec

req = ["darker[black,color,isort]"]
if VERSION:
    if VERSION.startswith("@"):
        req[0] += f"@git+https://github.com/akaihola/darker{VERSION}"
    elif VERSION.startswith(("~", "=", "<", ">")):
        req[0] += VERSION
    else:
        req[0] += f"=={VERSION}"

pip_install(*req)


base_cmd = [str(ENV_BIN / "darker")]
proc = run(  # nosec
    [
        *base_cmd,
        *shlex.split(OPTIONS),
        "--revision",
        REVISION,
        *shlex.split(SRC),
    ],
    check=False,
    stdout=PIPE,
    stderr=STDOUT,
    env={**os.environ, "PATH": f"{ENV_BIN}:{os.environ['PATH']}"},
    encoding="utf-8",
    cwd=WORKING_DIRECTORY,
)
print(proc.stdout, end="")

set_github_output("stdout", proc.stdout)
exit_with_exitcode(proc.returncode)
