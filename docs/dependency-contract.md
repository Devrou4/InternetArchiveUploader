# Dependency contract

Baseline: upstream commit `5aaea69`, Python 3.11, internetarchive 5.11.1,
PySide6 6.11.2 (pinned in `requirements.txt`).

Verified by `tests/test_dependency_contract.py`:

- `get_session(config_file=...)` builds an `ArchiveSession` bound to that file.
- `ArchiveSession.get_item(identifier)` is the only supported way to build an
  `Item`; `ia.Item(...)` directly fails with `'str' object has no attribute
  'protocol'`.
- `Item.load()` sets `exists` from `bool(item_metadata)`. A failed metadata
  fetch leaves the item unloaded, so callers must treat "no metadata" and
  "query failed" differently.
- `Session.get_metadata(identifier)` returns `None` on failure instead of raising.
- `Item.upload_file(..., key=..., metadata=..., validate_identifier=...)` sends
  one file; `metadata` is only meaningful when creating the item.
- `internetarchive.upload` returns `requests.Response` objects; success is
  `response.status_code == 200`.
- Public exceptions: `AuthenticationError`, `AccountAPIError`,
  `InvalidChecksumError`, `DirectoryTraversalError`, `ItemLocateError`.
- `internetarchive` has no documented upload progress callback; the plan's
  "no fabricated percentage" rule applies until a verified hook exists.

Identifier lowercasing is NOT applied by this project. Any restriction is
enforced server-side and surfaced as an error.
