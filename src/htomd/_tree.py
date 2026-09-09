"""Ordered, private HTML tree and stack-safe traversals."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

SPACE = re.compile(r"\s+")


@dataclass(eq=False, slots=True)
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Node | str] = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)


def walk(root: Node) -> Iterator[Node]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        for child in reversed(node.children):
            if isinstance(child, Node):
                stack.append(child)


def postorder(root: Node, *, leaf_tags: frozenset[str] = frozenset()) -> Iterator[Node]:
    """Visit children before parents, without descending into literal leaf tags."""
    stack = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if visited or node.tag in leaf_tags:
            yield node
            continue
        stack.append((node, True))
        for child in reversed(node.children):
            if isinstance(child, Node):
                stack.append((child, False))


def text_content(root: Node, *, normalize: bool = True) -> str:
    pieces: list[str] = []
    stack: list[Node | str] = [root]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            pieces.append(item)
        else:
            stack.extend(reversed(item.children))
    value = "".join(pieces)
    return SPACE.sub(" ", value).strip() if normalize else value


def elements(node: Node) -> list[Node]:
    return [child for child in node.children if isinstance(child, Node)]
