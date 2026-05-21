from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import unquote


@dataclass(slots=True)
class BrowserAuthConfig:
    interactive_login: bool = False
    login_wait_timeout_ms: int = 180_000
    login_poll_interval_ms: int = 1_000
    login_url_keywords: tuple[str, ...] = (
        "login",
        "signin",
        "sign-in",
        "auth",
        "sso",
        "oauth",
        "account",
    )
    login_html_keywords: tuple[str, ...] = (
        "sign in",
        "log in",
        "login",
        "signin",
        "password",
        "username",
        "email",
        "登录",
        "密码",
        "账号",
    )
    success_url_patterns: tuple[str, ...] = ()
    success_selectors: tuple[str, ...] = ()


@dataclass(slots=True)
class AuthDetectionResult:
    login_required: bool
    confidence: float
    reason: str
    source_url: str
    final_url: str
    redirect_chain: list[str] = field(default_factory=list)
    matched_url_keywords: list[str] = field(default_factory=list)
    matched_html_keywords: list[str] = field(default_factory=list)
    source_url_in_final_url: bool = False
    has_redirect_history: bool = False
    has_password_input: bool = False
    has_source_url_hint_in_html: bool = False
    text_density_score: float = 0.0


@dataclass(slots=True)
class LoginWaitResult:
    success: bool
    reason: str
    before_url: str
    after_url: str
    before_density_score: float
    after_density_score: float
    waited_ms: float
    final_html_len: int = 0


class AuthGate:
    def __init__(self, config: BrowserAuthConfig | None = None) -> None:
        self.config = config or BrowserAuthConfig()

    def detect(
        self,
        *,
        source_url: str,
        final_url: str,
        html: str,
        redirect_chain: list[str] | None = None,
    ) -> AuthDetectionResult:
        redirect_chain = list(redirect_chain or [])
        score = 0.0
        reasons: list[str] = []
        url_match, matched_url_keywords = self.looks_like_login_url(final_url)
        html_match, matched_html_keywords, has_password_input = self.looks_like_login_html(html)
        source_url_in_final_url = self._contains_unquoted(source_url, final_url)
        has_source_url_hint_in_html = self._contains_unquoted(source_url, html[:200_000])
        has_redirect_history = bool(redirect_chain)

        if has_redirect_history:
            score += 0.15
            reasons.append("redirect_history")
        if url_match:
            score += 0.25
            reasons.append("login_url_keyword")
        if has_password_input:
            score += 0.35
            reasons.append("password_input")
        if html_match:
            score += 0.15
            reasons.append("login_html_keyword")
        if source_url_in_final_url:
            score += 0.10
            reasons.append("source_url_in_final_url")
        if has_source_url_hint_in_html:
            score += 0.10
            reasons.append("source_url_hint_in_html")

        confidence = min(score, 1.0)
        login_required = confidence >= 0.45
        text_density_score = self.compute_text_density_score(html)
        reason = ",".join(reasons) if reasons else "no_auth_signals"
        return AuthDetectionResult(
            login_required=login_required,
            confidence=confidence,
            reason=reason,
            source_url=source_url,
            final_url=final_url,
            redirect_chain=redirect_chain,
            matched_url_keywords=matched_url_keywords,
            matched_html_keywords=matched_html_keywords,
            source_url_in_final_url=source_url_in_final_url,
            has_redirect_history=has_redirect_history,
            has_password_input=has_password_input,
            has_source_url_hint_in_html=has_source_url_hint_in_html,
            text_density_score=text_density_score,
        )

    def compute_text_density_score(self, html: str) -> float:
        lower = (html or "").lower()
        lower = re.sub(r"<script[\s\S]*?</script>", " ", lower)
        lower = re.sub(r"<style[\s\S]*?</style>", " ", lower)
        text = re.sub(r"<[^>]+>", " ", lower)
        text = re.sub(r"\s+", " ", text).strip()
        text_len = len(text)
        html_len = max(len(html or ""), 1)
        link_count = len(re.findall(r"<a\b", lower))
        input_count = len(re.findall(r"<input\b", lower))
        password_count = len(re.findall(r"type\s*=\s*[\"']?password", lower))
        density = text_len / html_len
        score = density
        score += min(text_len / 5000.0, 0.5)
        score -= min(link_count / 200.0, 0.2)
        score -= min(input_count / 100.0, 0.2)
        score -= min(password_count * 0.3, 0.6)
        return max(0.0, min(score, 1.0))

    def looks_like_login_url(self, url: str) -> tuple[bool, list[str]]:
        lower = unquote(url or "").lower()
        matched = [keyword for keyword in self.config.login_url_keywords if keyword.lower() in lower]
        return bool(matched), matched

    def looks_like_login_html(self, html: str) -> tuple[bool, list[str], bool]:
        lower = unquote(html or "").lower()
        matched = [keyword for keyword in self.config.login_html_keywords if keyword.lower() in lower]
        has_password_input = bool(re.search(r"<input\b[^>]*type\s*=\s*[\"']?password", lower))
        return bool(matched), matched, has_password_input

    def success_url_matches(self, url: str) -> bool:
        lower = unquote(url or "").lower()
        return any(pattern.lower() in lower for pattern in self.config.success_url_patterns)

    def source_url_in_current_url(self, source_url: str, current_url: str) -> bool:
        return self._contains_unquoted(source_url, current_url)

    def _contains_unquoted(self, needle: str, haystack: str) -> bool:
        if not needle or not haystack:
            return False
        return unquote(needle) in unquote(haystack)


def now_ms() -> float:
    return time.monotonic() * 1000.0
