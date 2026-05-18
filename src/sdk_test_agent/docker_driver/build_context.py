from __future__ import annotations

import io
import tarfile


def make_tar_context(
    dockerfile_text: str | None,
    dockerfile_path: str = "Dockerfile",
    files: dict[str, bytes] | None = None,
) -> bytes:
    """Build an in-memory tar build context from Dockerfile text and files."""

    members = dict(files or {})
    if dockerfile_text is not None:
        members[dockerfile_path] = dockerfile_text.encode("utf-8")

    if not members:
        raise ValueError("empty build context: provide dockerfile_text and/or files")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, raw in sorted(members.items()):
            info = tarfile.TarInfo(name=name.lstrip("/"))
            info.size = len(raw)
            tf.addfile(info, io.BytesIO(raw))
    return buf.getvalue()
