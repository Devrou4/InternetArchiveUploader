"""Conservative media-type detection.

Only formats whose bytes we can confirm are classified automatically.
Archives and unknown payloads stay uncertain: a ZIP may hold a book, a ROM,
or a dataset, and guessing would corrupt item metadata.
"""

from dataclasses import dataclass
from pathlib import Path

HEADER_BYTES = 32

EXTENSION_MAP = {
    ".mp3": "audio",
    ".flac": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".opus": "audio",
    ".m4a": "audio",
    ".mp4": "movies",
    ".mkv": "movies",
    ".webm": "movies",
    ".avi": "movies",
    ".mov": "movies",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
    ".tif": "image",
    ".tiff": "image",
    ".pdf": "texts",
    ".epub": "texts",
    ".txt": "texts",
    ".djvu": "texts",
    ".nsp": "software",
    ".xci": "software",
    ".iso": "software",
}

UNCERTAIN_EXTENSIONS = {".zip", ".7z", ".rar", ".tar", ".gz", ".bin?"}


def _header_mediatype(head: bytes) -> str | None:
    if head.startswith(b"ID3") or head.startswith(b"fLaC") or head.startswith(b"OggS"):
        return "audio"
    if head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8\xff") or head.startswith(b"GIF8"):
        return "image"
    if head.startswith(b"%PDF"):
        return "texts"
    if head[4:8] == b"ftyp" or head.startswith(b"\x1aE\xdf\xa3"):
        return "movies"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"7z\xbc\xaf"):
        return "7z"
    if head.startswith(b"Rar!"):
        return "rar"
    if head.startswith(b"NSP") or head.startswith(b"XCI"):
        return "software"
    return None


@dataclass(frozen=True)
class Detection:
    mediatype: str | None
    reason: str
    needs_confirmation: bool


def _uncertain(reason: str) -> Detection:
    return Detection(mediatype=None, reason=reason, needs_confirmation=True)


def detect_file(path: Path) -> Detection:
    path = Path(path)
    if not path.is_file():
        return _uncertain("Not a readable regular file")

    try:
        head = path.read_bytes()[:HEADER_BYTES]
    except OSError:
        return _uncertain("Cannot read file header")

    by_extension = EXTENSION_MAP.get(path.suffix.lower())
    header_kind = _header_mediatype(head)

    if header_kind is None:
        if by_extension:
            return Detection(
                mediatype=by_extension,
                reason=f"Extension {path.suffix.lower()} only; header not recognised",
                needs_confirmation=False,
            )
        return _uncertain("Unknown format; choose the media type manually")

    if header_kind in {"zip", "7z", "rar"}:
        if path.suffix.lower() == ".epub":
            return Detection("texts", "EPUB container detected", False)
        return _uncertain("Archive container; contents decide the media type")

    if header_kind == "texts" and by_extension in {"texts", None}:
        return Detection("texts", "Document header detected", False)
    if header_kind == "texts" and by_extension != "texts":
        return _uncertain("Extension and file header disagree")

    if by_extension and by_extension != header_kind:
        return _uncertain("Extension and file header disagree")

    return Detection(header_kind, "File header detected", False)