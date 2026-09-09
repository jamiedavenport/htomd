"""Read explicit metadata before cleanup, then refine it from selected content."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace

from ._models import Metadata
from ._tree import Node, text_content, walk
from ._urls import safe_url

ARTICLE_TYPES = frozenset(
    {
        "Article",
        "NewsArticle",
        "BlogPosting",
        "TechArticle",
        "ScholarlyArticle",
        "MedicalScholarlyArticle",
        "Report",
        "AnalysisNewsArticle",
        "OpinionNewsArticle",
        "ReviewNewsArticle",
        "BackgroundNewsArticle",
        "APIReference",
        "LiveBlogPosting",
    }
)


def string(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def json_articles(value: object) -> Iterator[dict[str, object]]:
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(reversed(item))
        elif isinstance(item, dict):
            kind = item.get("@type", [])
            kinds = [kind] if isinstance(kind, str) else kind
            if isinstance(kinds, list) and any(
                isinstance(entry, str) and entry.rsplit("/", 1)[-1] in ARTICLE_TYPES
                for entry in kinds
            ):
                yield item
            graph = item.get("@graph")
            if isinstance(graph, (dict, list)):
                stack.append(graph)


def author_name(value: object) -> str | None:
    if isinstance(value, str):
        return string(value)
    if isinstance(value, dict):
        return string(value.get("name"))
    if isinstance(value, list):
        names = [name for entry in value if (name := author_name(entry))]
        return ", ".join(names) or None
    return None


def read_jsonld(node: Node) -> dict[str, object]:
    if node.attrs.get("type", "").lower() != "application/ld+json":
        return {}
    try:
        value = json.loads(text_content(node, normalize=False))
    except (ValueError, RecursionError):
        return {}
    return next(json_articles(value), {})


def read_metadata(root: Node, url: str | None, base: str | None) -> Metadata:
    fields: dict[str, str] = {}
    article: dict[str, object] = {}
    title = language = canonical = None
    for node in walk(root):
        if node.tag == "meta":
            key = node.attrs.get("property", node.attrs.get("name", "")).lower()
            content = string(node.attrs.get("content"))
            if content:
                fields.setdefault(key, content)
        elif node.tag == "title" and title is None:
            title = string(text_content(node))
        elif node.tag == "html":
            language = string(node.attrs.get("lang") or node.attrs.get("xml:lang"))
        elif node.tag == "link" and "canonical" in node.attrs.get("rel", "").lower().split():
            canonical = canonical or safe_url(node.attrs.get("href", ""), base) or None
        elif node.tag == "script" and not article:
            article = read_jsonld(node)
    return Metadata(
        title=fields.get("og:title") or title or string(article.get("headline")),
        author=fields.get("author") or author_name(article.get("author")),
        description=fields.get("description")
        or fields.get("og:description")
        or string(article.get("description")),
        language=language or string(article.get("inLanguage")) or fields.get("og:locale"),
        published_time=fields.get("article:published_time")
        or fields.get("date")
        or string(article.get("datePublished")),
        url=url,
        canonical_url=canonical,
    )


def refine_metadata(metadata: Metadata, selected: list[Node]) -> Metadata:
    heading = None
    author = metadata.author or None
    published = metadata.published_time or None
    for root in selected:
        for node in walk(root):
            if node.tag == "h1" and heading is None:
                heading = string(text_content(node))
            if author is None and local_author(node):
                author = string(text_content(node))
            if (
                published is None
                and node.tag == "time"
                and node.attrs.get("itemprop") != "dateModified"
            ):
                published = string(node.attrs.get("datetime")) or string(text_content(node))
    return replace(
        metadata,
        title=heading or metadata.title,
        author=metadata.author or author,
        published_time=metadata.published_time or published,
    )


def local_author(node: Node) -> bool:
    if node.attrs.get("itemprop") == "author" or "author" in node.attrs.get("rel", "").split():
        return True
    tokens = node.attrs.get("class", "").lower().split()
    return any(token in {"byline", "author", "p-author"} for token in tokens)
