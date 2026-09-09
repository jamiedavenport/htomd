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
        stack.extend(child for child in reversed(node.children) if isinstance(child, Node))


def postorder(root: Node) -> Iterator[Node]:
    stack = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if visited:
            yield node
            continue
        stack.append((node, True))
        stack.extend((child, False) for child in reversed(node.children) if isinstance(child, Node))


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
