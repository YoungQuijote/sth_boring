from __future__ import annotations

from dataclasses import dataclass

from agent_crawler.models import ArtifactRefs, CrawlResultBundle


@dataclass
class ArtifactAdapterForCrawler:
    artifact_manager: object | None = None

    def persist(self, bundle: CrawlResultBundle) -> ArtifactRefs:
        if self.artifact_manager is None:
            return ArtifactRefs()
        raise NotImplementedError("Project-level artifact_manager integration will be added in a later iteration.")
