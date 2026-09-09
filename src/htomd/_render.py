"""Stack-safe Markdown serialization, independent of selection heuristics."""

from __future__ import annotations

import re

from ._selection import HEADINGS
from ._tree import SPACE, Node, elements, postorder, text_content
from ._urls import destination, safe_url

EMPHASIS = {"em": "*", "i": "*", "strong": "**", "b": "**", "s": "~~", "del": "~~", "strike": "~~"}
BLOCKS = frozenset(
    {
        "p",
        "div",
        "article",
        "main",
        "section",
        "header",
        "footer",
        "figure",
        "figcaption",
        "address",
        "details",
        "summary",
        "dl",
    }
)
MARKUP = re.compile(r"([\\`*_~\[\]])")
BLOCK_START = re.compile(r"(^|\n)(\s*)(#{1,6}(?=\s)|[-+](?=\s)|\d+[.)](?=\s)|[=~-]{3,}(?=\s|$))")


def escape(value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = MARKUP.sub(r"\\\1", value)
    return BLOCK_START.sub(escape_block_start, value)


def escape_block_start(match: re.Match[str]) -> str:
    marker = match[3]
    if marker[0].isdigit():
        marker = marker[:-1] + "\\" + marker[-1]
    else:
        marker = "\\" + marker
    return match[1] + match[2] + marker


def longest_run(value: str, character: str) -> int:
    return max(
        (len(match[0]) for match in re.finditer(re.escape(character) + "+", value)), default=0
    )


def inline_code(node: Node) -> str:
    value = (
        text_content(node, normalize=False)
        .replace("\r\n", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    if not value:
        return ""
    delimiter = "`" * (longest_run(value, "`") + 1)
    padding = (
        " "
        if value.startswith("`")
        or value.endswith("`")
        or (value.startswith(" ") and value.endswith(" ") and value.strip())
        else ""
    )
    return delimiter + padding + value + padding + delimiter


def code_language(node: Node) -> str:
    candidates = [node, *elements(node)]
    if node.parent is not None:
        candidates.append(node.parent)
    for candidate in candidates:
        for token in candidate.attrs.get("class", "").split():
            if token.startswith(("language-", "lang-", "highlight-")):
                value = token.split("-", 1)[1]
                if re.fullmatch(r"[\w.+#-]+", value):
                    return value
        value = candidate.attrs.get("data-language", "")
        if re.fullmatch(r"[\w.+#-]+", value):
            return value
    return ""


def fenced_code(node: Node) -> str:
    value = text_content(node, normalize=False).replace("\r\n", "\n").replace("\r", "\n")
    fence = "`" * max(3, longest_run(value, "`") + 1)
    ending = "" if value.endswith("\n") else "\n"
    return f"\n\n{fence}{code_language(node)}\n{value}{ending}{fence}\n\n"


def join_parts(parts: list[str]) -> str:
    """Coalesce block boundaries without touching whitespace inside code blocks."""
    result: list[str] = []
    for part in parts:
        if not part:
            continue
        if result and result[-1].endswith("\n") and part.startswith("\n"):
            result[-1] = result[-1].rstrip("\n")
            part = "\n\n" + part.lstrip("\n")
        result.append(part)
    return "".join(result)


def wrap_inline(body: str, marker: str) -> str:
    content = body.strip()
    if not content:
        return body
    leading = " " if body[:1].isspace() else ""
    trailing = " " if body[-1:].isspace() else ""
    return leading + marker + content + marker + trailing


def render_link(node: Node, body: str, base: str | None) -> str:
    href = safe_url(node.attrs.get("href", ""), base)
    if not href or not body.strip():
        return body
    return f"[{body.strip()}]({destination(href)})"


def render_image(node: Node, base: str | None) -> str:
    alt = escape(SPACE.sub(" ", node.attrs.get("alt", "")).strip())
    source = safe_url(node.attrs.get("src", ""), base)
    if not source or not node.attrs.get("src"):
        return alt
    return f"![{alt}]({destination(source)})"


def render_list(node: Node, rendered: dict[Node, str]) -> str:
    try:
        number = int(node.attrs.get("start", "1"))
    except ValueError:
        number = 1
    items = []
    for child in elements(node):
        if child.tag != "li":
            continue
        if node.tag == "ol":
            value = child.attrs.get("value", "")
            if re.fullmatch(r"-?\d{1,9}", value):
                number = int(value)
        marker = f"{number}. " if node.tag == "ol" else "- "
        lines = rendered[child].strip().splitlines()
        if lines:
            continuation = [" " * len(marker) + line if line else "" for line in lines[1:]]
            items.append("\n".join([marker + lines[0], *continuation]))
        number += 1
    return "\n" + "\n".join(items) + "\n" if items else ""


def table_rows(node: Node) -> list[Node]:
    rows = []
    stack = list(reversed(elements(node)))
    while stack:
        child = stack.pop()
        if child.tag == "tr":
            rows.append(child)
        elif child.tag in {"thead", "tbody", "tfoot"}:
            stack.extend(reversed(elements(child)))
    return rows


def simple_table(rows: list[list[Node]]) -> bool:
    if not rows or not rows[0] or len({len(row) for row in rows}) != 1:
        return False
    for row in rows:
        for cell in row:
            if cell.attrs.get("colspan", "1") != "1" or cell.attrs.get("rowspan", "1") != "1":
                return False
            if any(child.tag in {"table", "pre", "ul", "ol", "p"} for child in elements(cell)):
                return False
    return True


def render_table(node: Node, rendered: dict[Node, str]) -> str:
    rows = [
        [cell for cell in elements(row) if cell.tag in {"th", "td"}] for row in table_rows(node)
    ]
    captions = [rendered[child].strip() for child in elements(node) if child.tag == "caption"]
    if not simple_table(rows):
        lines = []
        for index, row in enumerate(rows, 1):
            cell_values = [rendered[cell].strip().replace("\n", " ") for cell in row]
            lines.append(f"{index}. " + " — ".join(cell_values))
        return "\n\n" + "\n\n".join([*captions, "\n".join(lines)]) + "\n\n"
    values = [
        [rendered[cell].strip().replace("|", "\\|").replace("\n", " ") for cell in row]
        for row in rows
    ]
    if not any(cell.tag == "th" for cell in rows[0]):
        values.insert(0, [""] * len(rows[0]))
    values.insert(1, ["---"] * len(rows[0]))
    lines = ["| " + " | ".join(row) + " |" for row in values]
    return "\n\n" + "\n\n".join([*captions, "\n".join(lines)]) + "\n\n"


def serialize(node: Node, body: str, rendered: dict[Node, str], base: str | None) -> str:
    tag = node.tag
    if tag in HEADINGS:
        return "\n\n" + "#" * int(tag[1]) + " " + body.strip() + "\n\n" if body.strip() else ""
    if tag in EMPHASIS:
        return wrap_inline(body, EMPHASIS[tag])
    if tag in {"code", "kbd", "samp"}:
        return inline_code(node)
    if tag == "pre":
        return fenced_code(node)
    if tag == "a":
        return render_link(node, body, base)
    if tag == "img":
        return render_image(node, base)
    if tag in {"ul", "ol"}:
        return render_list(node, rendered)
    if tag == "table":
        return render_table(node, rendered)
    return serialize_block(tag, body)


def serialize_block(tag: str, body: str) -> str:
    if tag == "blockquote":
        return (
            "\n\n"
            + "\n".join("> " + line if line else ">" for line in body.strip().splitlines())
            + "\n\n"
        )
    if tag == "br":
        return "  \n"
    if tag == "hr":
        return "\n\n---\n\n"
    if tag == "dt":
        return "\n\n" + wrap_inline(body.strip(), "**") + "\n"
    if tag == "dd":
        return "\n" + body.strip() + "\n\n"
    if tag in BLOCKS:
        return "\n\n" + body.strip() + "\n\n" if body.strip() else ""
    return body


def child_parts(node: Node, rendered: dict[Node, str]) -> list[str]:
    parts = []
    block_tags = BLOCKS | HEADINGS | {"ul", "ol", "pre", "table", "blockquote", "hr", "li"}
    for index, child in enumerate(node.children):
        if isinstance(child, Node):
            parts.append(rendered[child])
            continue
        if child.isspace():
            neighbors = (
                node.children[max(0, index - 1) : index] + node.children[index + 1 : index + 2]
            )
            if any(isinstance(other, Node) and other.tag in block_tags for other in neighbors):
                continue
        parts.append(escape(SPACE.sub(" ", child)))
    return parts


def render(selected: list[Node], base: str | None) -> str:
    output = []
    for root in selected:
        rendered: dict[Node, str] = {}
        for node in postorder(root):
            parts = child_parts(node, rendered)
            body = join_parts(parts)
            rendered[node] = serialize(node, body, rendered, base)
        output.append(rendered[root])
    result = join_parts(output).strip()
    return result + "\n" if result else ""
