"""Focused Markdown and metadata from decoded HTML, with no network access."""

from ._metadata import read_metadata, refine_metadata
from ._models import Diagnostics, Document, Metadata
from ._parser import parse
from ._render import render
from ._selection import select
from ._urls import document_base

__all__ = ["Diagnostics", "Document", "Metadata", "convert", "extract"]


def extract(html: str, *, url: str | None = None) -> Document:
    """Extract relevant Markdown and explicit metadata from an HTML string.

    ``url`` provides source context and resolves references; no fetching occurs.
    Malformed HTML receives best-effort recovery. Result dataclasses are immutable.
    """
    if not isinstance(html, str):
        raise TypeError("html must be a decoded str")
    if url is not None and not isinstance(url, str):
        raise TypeError("url must be a str or None")
    root, parsing_notes = parse(html)
    base = document_base(root, url)
    metadata = read_metadata(root, url, base)
    selected, diagnostics = select(root)
    metadata = refine_metadata(metadata, selected)
    markdown = render(selected, base)
    diagnostics = Diagnostics(
        diagnostics.strategy if markdown else "none", parsing_notes + diagnostics.notes
    )
    return Document(markdown, metadata, diagnostics)


def convert(html: str, *, url: str | None = None) -> str:
    """Return the Markdown produced by :func:`extract`."""
    return extract(html, url=url).markdown
