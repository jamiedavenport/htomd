from htomd._parser import parse
from htomd._tree import elements, text_content, walk


def test_order_and_single_entity_decode() -> None:
    root, _ = parse("<p>A &amp;amp; <em>B</em> C &#x1f375;</p>")
    paragraph = elements(root)[0]
    assert paragraph.children[0] == "A &amp; "
    assert text_content(root) == "A &amp; B C 🍵"


def test_optional_paragraph_closure() -> None:
    root, _ = parse("<p>one<p>two<div>three</div>")
    assert [node.tag for node in elements(root)] == ["p", "p", "div"]


def test_scoped_list_closure() -> None:
    root, _ = parse("<ul><li>A<ul><li>B<li>C</ul><li>D</ul>")
    outer = elements(root)[0]
    assert [text_content(node) for node in elements(outer)] == ["ABC", "D"]
    nested = elements(elements(outer)[0])[0]
    assert [text_content(node) for node in elements(nested)] == ["B", "C"]


def test_scoped_table_closure() -> None:
    root, _ = parse("<table><tr><td>A<td>B<tr><td>C<td>D</table>")
    rows = elements(elements(root)[0])
    assert [[text_content(cell) for cell in elements(row)] for row in rows] == [
        ["A", "B"],
        ["C", "D"],
    ]


def test_nested_table_does_not_close_outer_cell() -> None:
    root, _ = parse("<table><tr><td>A<table><tr><td>B</table>C<td>D</table>")
    outer_row = elements(elements(root)[0])[0]
    assert [text_content(cell) for cell in elements(outer_row)] == ["ABC", "D"]


def test_unmatched_closing_tag_and_void_elements() -> None:
    root, notes = parse("</bad><p>A<br>B<img src=x>C</p>")
    assert text_content(root) == "ABC"
    assert notes
    assert [node.tag for node in elements(elements(root)[0])] == ["br", "img"]


def test_deep_nesting_is_iterative() -> None:
    root, _ = parse("<div>" * 3000 + "deep" + "</div>" * 3000)
    assert len(list(walk(root))) == 3001
    assert text_content(root) == "deep"


def test_preformatted_whitespace() -> None:
    root, _ = parse("<pre>\n  a\t&amp;\n b\n</pre>")
    assert text_content(root, normalize=False) == "\n  a\t&\n b\n"


def test_unclosed_comment_does_not_become_content() -> None:
    root, _ = parse("<p>kept</p><!-- unfinished")
    assert text_content(root) == "kept"
