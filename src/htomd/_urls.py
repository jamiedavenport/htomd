"""Resolve references without fetching; reject active or unknown schemes."""

import re
from urllib.parse import quote, urljoin, urlsplit

from ._tree import Node, walk

SAFE_SCHEMES = frozenset({"", "http", "https", "mailto", "tel", "ftp"})
CONTROL = re.compile(r"[\x00-\x20\x7f]+")


def safe_url(value: str, base: str | None = None) -> str | None:
    value = value.strip()
    # Browsers ignore ASCII control characters in schemes. Check the normalized
    # spelling so an entity-encoded newline cannot disguise javascript:.
    checked = CONTROL.sub("", value)
    try:
        if urlsplit(checked).scheme.lower() not in SAFE_SCHEMES:
            return None
        resolved = urljoin(base, value) if base else value
        if urlsplit(CONTROL.sub("", resolved)).scheme.lower() not in SAFE_SCHEMES:
            return None
    except ValueError:
        return None
    return resolved


def document_base(root: Node, url: str | None) -> str | None:
    source = safe_url(url) if url else None
    for node in walk(root):
        if node.tag != "base" or "href" not in node.attrs:
            continue
        candidate = safe_url(node.attrs["href"], source)
        if candidate:
            parts = urlsplit(candidate)
            if parts.scheme in {"http", "https"} and parts.netloc:
                return candidate
    return source


def destination(value: str) -> str:
    # Parentheses and whitespace must not terminate a Markdown destination.
    return quote(value, safe="/:?#@!$&'*+,;=%[]~_-.")
