#!/usr/bin/env python3
"""Build a public knowledge-graph dataset from the generated site HTML."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


ROOT = Path(__file__).resolve().parent
SEARCH_INDEX = ROOT / "search-index.json"
OUTPUT = ROOT / "graph-data.json"
BASE_URL = "https://ydsl.local/"


class ArticleLinkParser(HTMLParser):
    def __init__(self, current_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.current_url = current_url
        self.in_article = False
        self.depth = 0
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key: value or "" for key, value in attrs}
        if tag == "article" and "content" in attrs_map.get("class", "").split():
            self.in_article = True
            self.depth = 1
            return
        if not self.in_article:
            return
        self.depth += 1
        if tag != "a":
            return
        href = attrs_map.get("href", "").strip()
        if href:
            self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_article:
            return
        self.depth -= 1
        if tag == "article" or self.depth <= 0:
            self.in_article = False
            self.depth = 0


def load_index() -> list[dict[str, str]]:
    return json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))


def group_for_url(url: str, category: str) -> str:
    if url == "index.html":
        return "home"
    if url.startswith("pages/teaching/"):
        return "teaching"
    if url.startswith("pages/projects/"):
        return "projects"
    if url.startswith("pages/concepts/"):
        return "concepts"
    if url.startswith("pages/entities/"):
        return "entities"
    if url.startswith("pages/synthesis/"):
        return "synthesis"
    return category or "other"


def html_path_for_url(url: str) -> Path:
    return ROOT / Path(url)


def normalize_target(current_url: str, href: str) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme and parsed.netloc and parsed.netloc != "ydsl.local":
        return None
    if href.startswith("#"):
        return current_url
    joined = urljoin(BASE_URL + current_url, href)
    parsed_joined = urlparse(joined)
    if parsed_joined.netloc != "ydsl.local":
        return None
    path = unquote(parsed_joined.path.lstrip("/"))
    if not path:
        path = "index.html"
    if path.endswith("/"):
        path += "index.html"
    return path


def title_sort_key(node: dict[str, str | int]) -> tuple[int, str]:
    match = re.search(r"/(\d+)-", str(node["url"]))
    number = int(match.group(1)) if match else 999
    return number, str(node["title"])


def main() -> None:
    index = load_index()
    nodes_by_url: dict[str, dict[str, str | int]] = {}

    for item in index:
        url = item["url"]
        nodes_by_url[url] = {
            "id": url,
            "title": item["title"],
            "url": url,
            "group": group_for_url(url, item.get("category", "")),
            "category": item.get("category", ""),
            "summary": item.get("summary", ""),
            "degree": 0,
        }

    edges: set[tuple[str, str]] = set()
    for source_url in nodes_by_url:
        html_path = html_path_for_url(source_url)
        if not html_path.exists():
            continue
        parser = ArticleLinkParser(source_url)
        parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
        for href in parser.links:
            target_url = normalize_target(source_url, href)
            if not target_url or target_url not in nodes_by_url or target_url == source_url:
                continue
            edges.add((source_url, target_url))

    degree = Counter()
    for source, target in edges:
        degree[source] += 1
        degree[target] += 1
    for url, count in degree.items():
        nodes_by_url[url]["degree"] = count

    nodes = sorted(nodes_by_url.values(), key=lambda node: (str(node["group"]), title_sort_key(node)))
    links = [{"source": source, "target": target} for source, target in sorted(edges)]

    graph = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "YDSL data citizen projects GitHub Pages",
        "nodeCount": len(nodes),
        "linkCount": len(links),
        "groups": {
            "home": "홈",
            "teaching": "강의 교안",
            "projects": "프로젝트",
            "concepts": "개념",
            "entities": "기관/도구",
            "synthesis": "종합",
            "other": "기타",
        },
        "nodes": nodes,
        "links": links,
    }
    OUTPUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(nodes)} nodes and {len(links)} links")


if __name__ == "__main__":
    main()
