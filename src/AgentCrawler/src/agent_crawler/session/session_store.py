from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from agent_crawler.models import TransportKind

from .auth_profile import AuthProfile


@dataclass
class CrawlSession:
    domain: str
    auth_profile: AuthProfile
    transport: TransportKind
    created_at_epoch: float = field(default_factory=time.time)
    last_used_epoch: float = field(default_factory=time.time)
    state: dict[str, object] = field(default_factory=dict)

    def touch(self) -> None:
        self.last_used_epoch = time.time()


class SessionStore:
    def __init__(self, *, ttl_s: float = 1800.0):
        self.ttl_s = ttl_s
        self._sessions: dict[tuple[str, str, TransportKind], CrawlSession] = {}

    def get(self, url_or_domain: str, auth_profile_id: str, transport: TransportKind) -> CrawlSession:
        domain = urlparse(url_or_domain).netloc.lower() or url_or_domain.lower()
        key = (domain, auth_profile_id, transport)
        now = time.time()
        session = self._sessions.get(key)
        if session and self.ttl_s > 0 and now - session.created_at_epoch > self.ttl_s:
            self.invalidate(domain=domain, auth_profile_id=auth_profile_id, transport=transport)
            session = None
        if session is None:
            session = CrawlSession(domain=domain, auth_profile=AuthProfile(profile_id=auth_profile_id), transport=transport)
            self._sessions[key] = session
        session.touch()
        return session

    def invalidate(self, *, domain: str, auth_profile_id: str | None = None, transport: TransportKind | None = None) -> None:
        for key in list(self._sessions):
            key_domain, key_profile, key_transport = key
            if key_domain != domain:
                continue
            if auth_profile_id is not None and key_profile != auth_profile_id:
                continue
            if transport is not None and key_transport != transport:
                continue
            self._sessions.pop(key, None)
