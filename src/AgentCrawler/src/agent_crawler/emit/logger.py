from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from agent_crawler.models import CrawlEvent


@dataclass
class EventLogger:
    jsonl_path: str | None = None
    stream: TextIO | None = None
    echo_stdout: bool = False

    def emit(self, event: CrawlEvent) -> None:
        payload = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        if self.jsonl_path:
            path = Path(self.jsonl_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(payload + "\n")
        if self.stream is not None:
            self.stream.write(payload + "\n")
            self.stream.flush()
        elif self.echo_stdout:
            sys.stdout.write(payload + "\n")
            sys.stdout.flush()
