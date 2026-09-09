"""Small HTMLParser-based recovery, without pretending to implement HTML5."""

from html.parser import HTMLParser

from ._tree import Node

VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)
P_BREAKERS = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "dl",
        "fieldset",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    ]
)
# A matching optional end tag must be found before its enclosing scope boundary.
IMPLIED: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "li": (frozenset({"li"}), frozenset({"ul", "ol"})),
    "dt": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "dd": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "tr": (frozenset({"tr"}), frozenset({"table", "tbody", "thead", "tfoot"})),
    "td": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "th": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "thead": (frozenset({"thead", "tbody", "tfoot"}), frozenset({"table"})),
    "tbody": (frozenset({"thead", "tbody", "tfoot"}), frozenset({"table"})),
    "tfoot": (frozenset({"thead", "tbody", "tfoot"}), frozenset({"table"})),
    "option": (frozenset({"option"}), frozenset({"select", "datalist"})),
}
END_SCOPES = {"li": {"ul", "ol"}, "td": {"tr", "table"}, "th": {"tr", "table"}, "tr": {"table"}}


class TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.recoveries = 0

    def close_in_scope(self, targets: frozenset[str], boundaries: frozenset[str]) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            tag = self.stack[index].tag
            if tag in targets:
                del self.stack[index:]
                self.recoveries += 1
                return
            if tag in boundaries:
                return

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in P_BREAKERS:
            self.close_in_scope(frozenset({"p"}), frozenset({"table", "td", "th", "li"}))
        if tag in IMPLIED:
            self.close_in_scope(*IMPLIED[tag])
        if tag == "a":
            self.close_in_scope(frozenset({"a"}), frozenset({"p", "div", "li"}))
        parent = self.stack[-1]
        node = Node(tag, {name: value or "" for name, value in attrs}, parent=parent)
        parent.children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            current = self.stack[index].tag
            if current == tag:
                del self.stack[index:]
                return
            if current in END_SCOPES.get(tag, set()):
                break
        self.recoveries += 1

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)

    def unknown_decl(self, data: str) -> None:
        self.recoveries += 1


def parse(html: str) -> tuple[Node, tuple[str, ...]]:
    parser = TreeParser()
    try:
        parser.feed(html)
        parser.close()
    except (AssertionError, ValueError):
        # HTMLParser rejects malformed marked sections. Preserve the parsed prefix.
        parser.recoveries += 1
    notes = ("Recovered malformed or optionally closed HTML.",) if parser.recoveries else ()
    return parser.root, notes
