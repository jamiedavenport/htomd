"""Immutable public results; the HTML tree is deliberately private."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Metadata:
    title: str | None = None
    author: str | None = None
    description: str | None = None
    language: str | None = None
    published_time: str | None = None
    url: str | None = None
    canonical_url: str | None = None


@dataclass(frozen=True, slots=True)
class Diagnostics:
    strategy: Literal["semantic", "scored", "fallback", "none"]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Document:
    markdown: str
    metadata: Metadata
    diagnostics: Diagnostics
