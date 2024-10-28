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

if os.getenv("INPUT_LINT", default=""):
    print(
        "::notice:: Baseline linting has been moved to the Graylint package."
        " See https://pypi.org/project/graylint for more information.",
    )

run([sys.executable, "-m", "venv", str(ENV_PATH)], check=True)  # nosec

req = ["darker[black,color,isort]"]
if VERSION:
    if VERSION.startswith("@"):
        req[0] = f"git+https://github.com/akaihola/darker{VERSION}#egg={req[0]}"
    elif VERSION.startswith(("~", "=", "<", ">")):
        req[0] += VERSION
    else:
        req[0] += f"=={VERSION}"

pip_proc = run(  # nosec
    [str(ENV_BIN / "python"), "-m", "pip", "install"] + req,
    check=False,
    stdout=PIPE,
    stderr=STDOUT,
    encoding="utf-8",
)
print(pip_proc.stdout, end="")
if pip_proc.returncode:
    print(f"::error::Failed to install {' '.join(req)}.", flush=True)
    sys.exit(pip_proc.returncode)


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
)
print(proc.stdout, end="")

sys.exit(proc.returncode)
