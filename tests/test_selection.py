"""Cleanup must keep cached evidence consistent with the surviving tree."""

import pytest

from htomd._parser import parse
from htomd._selection import clean, statistics, visible_tree
from htomd._tree import walk


@pytest.mark.parametrize(
    ("html", "removed"),
    [
        ("<article><h1>Tea</h1><p>Keep this.</p></article>", 0),
        (
            '<main><section><p>Keep, this.</p><aside class="related">Drop!</aside></section>'
            '<section><p><a href="/kept">A reference.</a></p>'
            '<div class="related"><a href="/drop">Drop?</a></div></section></main>',
            2,
        ),
        (
            '<main><div><section><p>Keep.</p><aside class="related">Drop.</aside></section>'
            '<aside class="related">Also drop.</aside></div>'
            '<table><tr><td>Cell</td></tr></table><pre>code</pre><img src="tea.png"></main>',
            2,
        ),
    ],
)
def test_cleanup_evidence_matches_fresh_accumulation(html: str, removed: int) -> None:
    root, _ = parse(html)
    root = visible_tree(root)
    cached, count = clean(root)
    fresh = statistics(root)
    assert count == removed
    assert {node: cached[node] for node in walk(root)} == fresh
