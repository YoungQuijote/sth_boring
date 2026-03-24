from __future__ import annotations

import io
import tarfile
from pathlib import Path


def pack_text_file(path: str, content: str) -> bytes:
    raw = content.encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo(name=path.lstrip("/"))
        info.size = len(raw)
        tf.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def pack_directory(local_dir: str) -> bytes:
    base = Path(local_dir)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for p in sorted(base.rglob("*")):
            tf.add(p, arcname=str(p.relative_to(base)))
    return buf.getvalue()


def unpack_archive(data: bytes, dest_dir: str) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        tf.extractall(path=dest_dir)
