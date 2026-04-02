from __future__ import annotations

from posixpath import normpath


def safe_join(workdir: str, rel_path: str) -> str:
    clean = normpath(rel_path).lstrip("/")
    if clean.startswith(".."):
        raise ValueError("path escapes workdir")
    return normpath(f"{workdir}/{clean}")
