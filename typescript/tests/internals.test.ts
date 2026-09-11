import assert from "node:assert/strict";
import { test } from "node:test";
import { parse } from "../dist/parser.js";
import { clean, statistics, visibleTree } from "../dist/selection.js";
import { elements, textContent, walk } from "../dist/tree.js";

test("optional closures respect nested list and table scopes", () => {
  const [list] = parse("<ul><li>A<ul><li>B<li>C</ul><li>D</ul>");
  assert.deepEqual(
    elements(elements(list)[0]!).map((node) => textContent(node)),
    ["ABC", "D"],
  );
  const [table] = parse("<table><tr><td>A<table><tr><td>B</table>C<td>D</table>");
  const row = elements(elements(table)[0]!)[0]!;
  assert.deepEqual(
    elements(row).map((node) => textContent(node)),
    ["ABC", "D"],
  );
});

test("cleanup cache matches fresh statistics for every surviving node", () => {
  const [root] = parse(
    '<main><div><section><p>Keep.</p><aside class="related">Drop.</aside></section><aside class="related">Also drop.</aside></div><table><tr><td>Cell</td></tr></table><pre>code</pre><img src="tea.png"></main>',
  );
  visibleTree(root);
  const [cached, removed] = clean(root);
  const fresh = statistics(root);
  assert.equal(removed, 2);
  for (const node of walk(root)) {
    assert.deepEqual(cached.get(node), fresh.get(node));
  }
});

test("entities decode once and unfinished comments are discarded", () => {
  const [root] = parse("<p>A &amp;amp; <em>B</em> C &#x1f375;</p><!-- unfinished");
  assert.equal(textContent(root), "A &amp; B C 🍵");
});
