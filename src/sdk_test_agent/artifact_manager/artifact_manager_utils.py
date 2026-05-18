from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:26].upper()}"


def ensure_task_dirs(root_dir: str, task_id: str) -> dict[str, str]:
    base = Path(root_dir) / task_id
    paths = {
        "root": str(base),
        "generated": str(base / "generated"),
        "logs": str(base / "logs"),
        "reports": str(base / "reports"),
        "inputs": str(base / "inputs"),
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
