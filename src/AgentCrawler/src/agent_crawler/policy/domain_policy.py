from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class DomainPolicy:
    domain: str
    prefer_browser: bool = False
    requires_auth: bool = False
    adapter_name: str | None = None
    prefer_profile: bool = False
    allow_llm_gate: bool = False
    allow_llm_render: bool = False
    result_cache_ttl_s: int = 600
    http_cache_ttl_s: int = 3600


@dataclass
class DomainPolicyRegistry:
    default_policy: DomainPolicy = field(default_factory=lambda: DomainPolicy(domain="*"))
    _policies: dict[str, DomainPolicy] = field(default_factory=dict)

    def register(self, policy: DomainPolicy) -> None:
        self._policies[policy.domain.lower()] = policy

    def resolve(self, url: str) -> DomainPolicy:
        host = urlparse(url).netloc.lower()
        if host in self._policies:
            return self._policies[host]
        parts = host.split(".")
        for idx in range(1, len(parts) - 1):
            wildcard = "*." + ".".join(parts[idx:])
            if wildcard in self._policies:
                return self._policies[wildcard]
        return self.default_policy
