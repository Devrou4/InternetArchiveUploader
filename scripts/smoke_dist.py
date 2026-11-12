"""Launch the packaged binary with --smoke-test."""

import subprocess
import sys
from pathlib import Path



def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: smoke_dist.py <bundle-dir>", file=sys.stderr)
        return 2
    binary = Path(argv[0]) / "InternetArchiveUploader"
    if not binary.is_file():
        print(f"missing binary: {binary}", file=sys.stderr)
        return 1
    return subprocess.call([str(binary), "--smoke-test"])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
