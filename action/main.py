import os
import shlex
import sys
from pathlib import Path
from subprocess import PIPE, STDOUT, run  # nosec

LINTER_WHITELIST = {"flake8", "pylint", "mypy"}
ACTION_PATH = Path(os.environ["GITHUB_ACTION_PATH"])
ENV_PATH = ACTION_PATH / ".darker-env"
ENV_BIN = ENV_PATH / ("Scripts" if sys.platform == "win32" else "bin")
OPTIONS = os.getenv("INPUT_OPTIONS", default="")
SRC = os.getenv("INPUT_SRC", default="")
VERSION = os.getenv("INPUT_VERSION", default="")
REVISION = os.getenv(
    "INPUT_REVISION", default=os.getenv("INPUT_COMMIT_RANGE", default="HEAD^")
)

run([sys.executable, "-m", "venv", str(ENV_PATH)], check=True)

req = ["darker[isort]"]
if VERSION:
    req[0] += f"=={VERSION}"
linter_options = []
for linter_ in os.getenv("INPUT_LINT", default="").split(","):
    linter = linter_.strip()
    if not linter:
        continue
    if linter not in LINTER_WHITELIST:
        raise RuntimeError(
            f"{linter!r} is not supported as a linter by the GitHub Action"
        )
    req.append(linter)
    linter_options.extend(["--lint", linter])

pip_proc = run(  # nosec
    [str(ENV_BIN / "python"), "-m", "pip", "install"] + req,
    check=False,
    stdout=PIPE,
    stderr=STDOUT,
    encoding="utf-8",
)
if pip_proc.returncode:
    print(pip_proc.stdout, end="")
    print(f"::error::Failed to install {' '.join(req)}.", flush=True)
    sys.exit(pip_proc.returncode)


base_cmd = [str(ENV_BIN / "darker")]
proc = run(  # nosec
    [
        *base_cmd,
        *shlex.split(OPTIONS),
        *linter_options,
        "--revision",
        REVISION,
        *shlex.split(SRC),
    ],
    check=False,
)

sys.exit(proc.returncode)
