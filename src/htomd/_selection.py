"""Select content using cached evidence, then clean only the selected region."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ._models import Diagnostics
from ._tree import Node, elements, postorder, walk

INERT = frozenset(
    [
        "head",
        "title",
        "meta",
        "link",
        "base",
        "script",
        "style",
        "template",
        "noscript",
        "iframe",
        "object",
        "embed",
        "svg",
        "canvas",
        "nav",
        "button",
        "input",
        "select",
        "textarea",
        "dialog",
    ]
)
NAV_ROLES = frozenset({"navigation", "banner", "contentinfo", "menu", "menubar", "dialog"})
STRUCTURES = frozenset({"ul", "ol", "dl", "table", "blockquote", "pre"})
CONTAINERS = frozenset({"article", "main", "section", "div", "body", "#document"})
EVIDENCE = frozenset({"p", "pre", "li", "dt", "dd", "td", "th", "blockquote"})
HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
NEGATIVE = frozenset(
    [
        "advertisement",
        "ads",
        "advert",
        "promo",
        "promotion",
        "related",
        "share",
        "sharing",
        "social",
        "cookie",
        "consent",
        "newsletter",
        "comments",
        "comment",
        "sidebar",
        "breadcrumb",
        "breadcrumbs",
        "pagination",
        "toolbar",
        "footer",
        "banner",
        "dropdown",
        "catlinks",
        "menu",
        "pager",
        "teaser",
        "toc",
        "well",
    ]
)
POSITIVE = frozenset(
    {"article", "content", "main", "post", "entry", "story", "text", "documentation"}
)
REFERENCES = frozenset({"footnotes", "references", "endnotes", "bibliography"})
PUNCTUATION = re.compile(r"[,.;:!?。，；：！？،؛]")
HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\s*(?:!important\s*)?(?:;|$)",
    re.I,
)
# Sibling recovery needs modest support, and can never escape its parent container.
SIBLING_SCORE_RATIO = 0.18
MAX_FALLBACK_BLOCKS = 256


@dataclass(slots=True)
class Stats:
    characters: int = 0
    linked: int = 0
    punctuation: int = 0
    blocks: int = 0
    headings: int = 0
    code: int = 0
    cells: int = 0
    images: int = 0
    controls: int = 0

    @property
    def density(self) -> float:
        return self.linked / max(1, self.characters)


def hints(node: Node) -> set[str]:
    value = node.attrs.get("class", "") + " " + node.attrs.get("id", "")
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def explicitly_hidden(node: Node) -> bool:
    return (
        "hidden" in node.attrs
        or node.attrs.get("aria-hidden", "").lower() == "true"
        or bool(HIDDEN_STYLE.search(node.attrs.get("style", "")))
    )


def visible_tree(root: Node) -> Node:
    """Copy visible content so metadata remains available on the original tree."""
    result = Node(root.tag, root.attrs.copy())
    stack = [(root, result, False)]
    while stack:
        original, target, local = stack.pop()
        local = local or original.tag in {"article", "main"} or original.attrs.get("role") == "main"
        for child in original.children:
            if isinstance(child, str):
                target.children.append(child)
                continue
            if excluded(child, local):
                continue
            copied = Node(child.tag, child.attrs.copy(), parent=target)
            target.children.append(copied)
            stack.append((child, copied, local))
    return result


def excluded(node: Node, local: bool) -> bool:
    if node.tag in INERT or explicitly_hidden(node):
        return True
    if node.tag == "a" and "headerlink" in hints(node):
        return node.attrs.get("href", "").startswith("#")
    role = node.attrs.get("role", "").lower()
    if role in NAV_ROLES:
        return True
    return node.tag in {"header", "footer"} and not local


def statistics(root: Node) -> dict[Node, Stats]:
    result: dict[Node, Stats] = {}
    for node in postorder(root):
        stat = Stats()
        for child in node.children:
            if isinstance(child, str):
                stat.characters += len(child.strip())
                stat.punctuation += len(PUNCTUATION.findall(child))
            else:
                other = result[child]
                for field in Stats.__slots__:
                    setattr(stat, field, getattr(stat, field) + getattr(other, field))
        stat.blocks += int(node.tag in EVIDENCE and stat.characters > 0)
        stat.headings += int(node.tag in HEADINGS and stat.characters > 0)
        stat.code += int(node.tag == "pre")
        stat.cells += int(node.tag in {"td", "th"})
        stat.images += int(node.tag == "img" and bool(node.attrs.get("src")))
        stat.controls += int(node.tag in {"form", "button", "input", "select", "textarea"})
        if node.tag == "a":
            stat.linked = stat.characters
        result[node] = stat
    return result


def conditional_clutter(node: Node, stat: Stats) -> bool:
    if node.tag in {"#document", "html", "body", "main", "article"}:
        return False
    tokens = hints(node)
    if tokens & REFERENCES or node.attrs.get("role") == "note":
        return False
    if not tokens & NEGATIVE or node.tag in EVIDENCE | HEADINGS:
        return False
    # Class hints alone never delete a node: require structural corroboration.
    if stat.density > 0.35 or stat.controls:
        return True
    if "footer" in tokens and stat.density > 0.15:
        return True
    if node.tag == "aside" and not stat.code and not stat.cells:
        return True
    if stat.blocks == 0 and stat.characters < 180:
        return True
    if tokens & {"comments", "comment"}:
        children = elements(node)
        return sum(bool(hints(child) & {"comment", "reply"}) for child in children) >= 2
    return False


def clean(root: Node) -> tuple[Node, int]:
    stats = statistics(root)
    removed = 0
    for node in walk(root):
        kept: list[Node | str] = []
        for child in node.children:
            if isinstance(child, Node) and conditional_clutter(child, stats[child]):
                removed += 1
            else:
                kept.append(child)
        node.children = kept
    return root, removed


def plausible(node: Node, stat: Stats, *, semantic: bool = False) -> bool:
    if not stat.characters:
        return bool(semantic and stat.images)
    if stat.code or stat.cells:
        return True
    if node.tag == "p" and stat.characters > stat.linked:
        return True
    if stat.density >= 0.8:
        return bool(semantic and stat.headings and stat.blocks)
    return node.tag in CONTAINERS | EVIDENCE | HEADINGS | STRUCTURES or semantic


def scores(root: Node, stats: dict[Node, Stats], *, relaxed: bool) -> dict[Node, float]:
    result: dict[Node, float] = {}
    for node in walk(root):
        stat = stats[node]
        if node.tag not in CONTAINERS or not plausible(node, stat):
            continue
        tokens = hints(node)
        score = math.sqrt(stat.characters) + min(stat.blocks, 30) * 2
        score += min(stat.punctuation, 40) * 0.25 + min(stat.code + stat.cells, 12) * 2
        score += 8 * bool(tokens & POSITIVE)
        if not relaxed:
            score -= 18 * bool(tokens & NEGATIVE)
        result[node] = score * (1 - stat.density) ** 2
    # Leaf evidence flows to nearby ancestors, without repeatedly counting nested blocks.
    for node in walk(root):
        if node.tag not in EVIDENCE or any(child.tag in EVIDENCE for child in elements(node)):
            continue
        stat = stats[node]
        support = (1 + min(stat.characters / 100, 3)) * (1 - stat.density)
        ancestor = node.parent
        for weight in (1.0, 0.5, 0.25):
            if ancestor is None:
                break
            if ancestor in result:
                result[ancestor] += support * weight
            ancestor = ancestor.parent
    return result


def semantic_candidate(
    root: Node, stats: dict[Node, Stats], ranked: dict[Node, float]
) -> Node | None:
    candidates = []
    landmarks = []
    for node in walk(root):
        landmark = node.tag == "main" or node.attrs.get("role") == "main"
        if not (landmark or node.tag == "article"):
            continue
        if not plausible(node, stats[node], semantic=True):
            continue
        if conditional_clutter(node, stats[node]):
            continue
        if "teaser" in hints(node) and stats[node].density > 0.1:
            continue
        candidates.append(node)
        if landmark:
            landmarks.append(node)
    candidates = landmarks or candidates
    if not candidates:
        return None
    return max(candidates, key=lambda node: ranked.get(node, 0))


def recover_siblings(
    winner: Node, stats: dict[Node, Stats], ranked: dict[Node, float]
) -> list[Node]:
    parent = winner.parent
    if parent is None:
        return [winner]
    threshold = max(5, ranked.get(winner, 0) * SIBLING_SCORE_RATIO)
    selected = []
    for sibling in elements(parent):
        stat = stats[sibling]
        if conditional_clutter(sibling, stat):
            continue
        supported = ranked.get(sibling, 0) >= threshold and stat.density < 0.5
        heading = sibling.tag in HEADINGS and stat.density < 0.5
        paragraph = sibling.tag == "p" and stat.density < 0.25 and bool(stat.characters)
        if sibling is winner or supported or heading or paragraph:
            selected.append(sibling)
    return selected


def fallback(root: Node, stats: dict[Node, Stats]) -> list[Node]:
    selected: list[Node] = []
    stack = [root]
    while stack and len(selected) < MAX_FALLBACK_BLOCKS:
        node = stack.pop()
        stat = stats[node]
        if conditional_clutter(node, stat):
            continue
        if (
            node.tag in EVIDENCE | HEADINGS | STRUCTURES
            and plausible(node, stat)
            or not elements(node)
            and stat.characters
            and stat.density < 0.5
        ):
            selected.append(node)
        else:
            stack.extend(reversed(elements(node)))
    return selected


def select(root: Node) -> tuple[list[Node], Diagnostics]:
    visible, removed = clean(visible_tree(root))
    stats = statistics(visible)
    ranked = scores(visible, stats, relaxed=False)
    notes = [f"Removed {removed} conditionally identified clutter blocks."] if removed else []
    winner = semantic_candidate(visible, stats, ranked)
    if winner is not None:
        return [winner], Diagnostics("semantic", tuple(notes))
    candidates = {
        node: score for node, score in ranked.items() if node.tag not in {"body", "#document"}
    }
    if not candidates or max(candidates.values()) < 5:
        notes.append("Retried selection once with relaxed class penalties.")
        ranked = scores(visible, stats, relaxed=True)
        candidates = {
            node: score for node, score in ranked.items() if node.tag not in {"body", "#document"}
        }
    if candidates and max(candidates.values()) >= 5:
        winner = max(candidates, key=lambda node: candidates[node])
        return recover_siblings(winner, stats, ranked), Diagnostics("scored", tuple(notes))
    recovered = fallback(visible, stats)
    notes.append(
        "Recovered plausible blocks." if recovered else "No relevant visible content found."
    )
    return recovered, Diagnostics("fallback" if recovered else "none", tuple(notes))
