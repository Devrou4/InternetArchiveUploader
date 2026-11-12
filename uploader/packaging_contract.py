"""Checks applied to a built bundle before it is published (Linux and Windows)."""

import sys
from pathlib import Path

BINARY_NAME = "InternetArchiveUploader"


def EXPECTED_BINARY(platform: str | None = None) -> str:
    """PyInstaller appends .exe on Windows only."""
    platform = sys.platform if platform is None else platform
    return f"{BINARY_NAME}.exe" if platform.startswith("win") else BINARY_NAME

REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "assets/Internet_Acrhive_Logo_White.png",
    "assets/Internet_Acrhive_Logo_Black.png",
    "assets/Internet_Archive_Icon.jpg",
)

FORBIDDEN_NAMES = frozenset({"ia.ini", ".ia.ini", "ia_upload_states"})


def _find(root: Path, relative: str) -> Path | None:
    """Accept both flat and PyInstaller's _internal/ data layout."""
    for base in (root, root / "_internal"):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    return None


def check_dist(root: Path, platform: str | None = None) -> list[str]:
    """Return a list of problems; empty means the bundle is acceptable."""
    root = Path(root)
    problems: list[str] = []

    if not root.is_dir():
        return [f"Bundle directory not found: {root}"]

    binary = EXPECTED_BINARY(platform)
    if not (root / binary).is_file():
        problems.append(f"Missing executable: {binary}")

    for relative in REQUIRED_FILES:
        if not _find(root, relative):
            problems.append(f"Missing required file: {relative}")

    for path in root.rglob("*"):
        if path.name in FORBIDDEN_NAMES:
            problems.append(f"Credential or state artifact in bundle: {path.relative_to(root)}")

    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_dist.py <bundle-dir>", file=sys.stderr)
        return 2
    problems = check_dist(Path(argv[0]))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print("bundle check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))