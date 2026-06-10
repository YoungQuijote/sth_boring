from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from ..models import Document


def _strip(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


@dataclass
class HtmlExtractor:
    """General-purpose extractor: title + main-ish text + outgoing links.

    For best results on messy sites, you can later swap this with:
      - trafilatura
      - readability-lxml
    """

    drop_selectors: tuple[str, ...] = (
        "script",
        "style",
        "noscript",
        "svg",
        "canvas",
        "header",
        "footer",
        "nav",
        "aside",
        "form",
    )

    def extract(self, html: str, *, url: str) -> Document:
        tree = HTMLParser(html)
        for sel in self.drop_selectors:
            for n in tree.css(sel):
                n.decompose()

        # title
        title = None
        tnode = tree.css_first("title")
        if tnode:
            title = _strip(tnode.text())

        # links
        links: List[str] = []
        for a in tree.css("a[href]"):
            href = (a.attributes.get("href") or "").strip()
            if not href:
                continue
            if href.startswith("#") or href.lower().startswith("javascript:"):
                continue
            abs_url = urljoin(url, href)
            links.append(abs_url)

        # main content heuristic
        main = tree.css_first("article") or tree.css_first("main") or tree.body
        text = ""
        if main:
            text = main.text(separator="\n")
        else:
            text = tree.text(separator="\n")

        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        return Document(url=url, title=title, text=text, links=links)


@dataclass
class WikiExtractor(HtmlExtractor):
    """Wikipedia-specific extraction: focus on #mw-content-text."""

    def extract(self, html: str, *, url: str) -> Document:
        tree = HTMLParser(html)
        for sel in self.drop_selectors:
            for n in tree.css(sel):
                n.decompose()

        title = None
        tnode = tree.css_first("h1#firstHeading") or tree.css_first("title")
        if tnode:
            title = _strip(tnode.text())

        content = tree.css_first("div#mw-content-text") or tree.css_first("div.mw-parser-output") or tree.body
        # Remove tables/infoboxes that often dominate
        if content:
            for n in content.css("table, div.navbox, div.reflist, ol.references, sup.reference"):
                n.decompose()

        links: List[str] = []
        for a in (content.css("a[href]") if content else tree.css("a[href]")):
            href = (a.attributes.get("href") or "").strip()
            if not href or href.startswith("#") or href.lower().startswith("javascript:"):
                continue
            abs_url = urljoin(url, href)
            links.append(abs_url)

        text = (content.text(separator="\n") if content else tree.text(separator="\n"))
        # remove wikipedia citation markers like [1]
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        return Document(url=url, title=title, text=text, links=links)
