"""Non-interactive startup check used by CI.

Runs the real entry point with --smoke-test so packaging problems (missing
Qt plugins, missing assets) fail the build instead of the user's desktop.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    return subprocess.call([sys.executable, str(ROOT / "main.py"), "--smoke-test"])


if __name__ == "__main__":
    raise SystemExit(main())
