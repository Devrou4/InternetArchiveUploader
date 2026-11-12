"""Checks applied to a built Linux bundle before it is published."""

import sys
from pathlib import Path

REQUIRED_FILES = (
    "main.py",
    "LICENSE",
    "README.md",
    "assets/Internet_Acrhive_Logo_White.png",
    "assets/Internet_Acrhive_Logo_Black.png",
    "assets/Internet_Archive_Icon.jpg",
)

FORBIDDEN_NAMES = frozenset({"ia.ini", ".ia.ini", "ia_upload_states"})


def check_dist(root: Path) -> list[str]:
    """Return a list of problems; empty means the bundle is acceptable."""
    root = Path(root)
    problems: list[str] = []

    if not root.is_dir():
        return [f"Bundle directory not found: {root}"]

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
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