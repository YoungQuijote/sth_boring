from __future__ import annotations

import importlib
import importlib.util
import re
from dataclasses import dataclass
from html.parser import HTMLParser as StdHTMLParser
from urllib.parse import urljoin

from webkit.models import Document


class _FallbackHTMLParser(StdHTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "a":
            attrs_dict = dict(attrs)
            href = (attrs_dict.get("href") or "").strip()
            if href and not href.startswith("#") and not href.lower().startswith("javascript:"):
                self.links.append(urljoin(self.base_url, href))
        if tag in {"p", "div", "section", "article", "main", "h1", "h2", "h3", "li", "br"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth and tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "section", "article", "main", "h1", "h2", "h3", "li"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


@dataclass
class UniversalExtractor:
    extractor: object | None = None

    def extract(self, html: str, *, url: str) -> Document:
        if self.extractor is not None:
            return self.extractor.extract(html, url=url)  # type: ignore[no-any-return, union-attr]
        if importlib.util.find_spec("selectolax") is not None:
            module = importlib.import_module("webkit.extractors.html")
            return module.HtmlExtractor().extract(html, url=url)
        parser = _FallbackHTMLParser(url)
        parser.feed(html)
        title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip() or None
        text = re.sub(r"[ \t]+", " ", "".join(parser.text_parts))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return Document(url=url, title=title, text=text, links=parser.links)


class HtmlExtractor(UniversalExtractor):
    pass


class WikiExtractor(UniversalExtractor):
    def extract(self, html: str, *, url: str) -> Document:
        if importlib.util.find_spec("selectolax") is not None:
            module = importlib.import_module("webkit.extractors.html")
            return module.WikiExtractor().extract(html, url=url)
        return super().extract(html, url=url)


__all__ = ["HtmlExtractor", "UniversalExtractor", "WikiExtractor"]
