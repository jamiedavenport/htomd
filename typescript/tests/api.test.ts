import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { convert, extract, type Document, type ExtractOptions } from "../dist/index.js";

interface Case {
  id: string;
  html: string;
  markdown: string;
  url?: string;
}

const cases = JSON.parse(
  readFileSync(new URL("../../tests/fixtures/synthetic/cases.json", import.meta.url), "utf8"),
) as Case[];
for (const fixture of cases) {
  test(fixture.id, () => {
    const document: Document = extract(fixture.html, { url: fixture.url });
    assert.equal(document.markdown, fixture.markdown);
    assert.equal(convert(fixture.html, { url: fixture.url }), document.markdown);
    assert.equal(Boolean(document.markdown), document.diagnostics.strategy !== "none");
  });
}

test("runtime input validation", () => {
  for (const value of [null, undefined, 1, Buffer.from("html"), [], {}, new String("html")]) {
    assert.throws(() => extract(value as string), { name: "TypeError", message: /html/ });
  }
  for (const value of [1, Buffer.from("url"), [], {}, new String("url")]) {
    assert.throws(() => extract("", { url: value } as ExtractOptions), {
      name: "TypeError",
      message: /url/,
    });
  }
  for (const url of [null, undefined]) {
    assert.equal(extract("", { url }).metadata.url, null);
  }
  assert.equal(extract("", { url: "" }).metadata.url, "");
});

test("results are immutable at runtime", () => {
  const result = extract("<p>Tea</p>");
  for (const value of [result, result.metadata, result.diagnostics, result.diagnostics.notes]) {
    assert.ok(Object.isFrozen(value));
    assert.throws(() => Object.assign(value, { extra: true }), TypeError);
  }
});

test("deep nesting is stack safe", () => {
  assert.equal(
    convert("<article>" + "<div>".repeat(3000) + "Text." + "</div>".repeat(3000) + "</article>"),
    "Text.\n",
  );
});

test("metadata precedence and camelCase API", () => {
  const result = extract(
    `<html lang="ja"><title>Document</title>
    <meta property="og:title" content="Open Graph"><meta name="author" content="Explicit">
    <meta name="description" content="Description"><link rel="canonical" href="/canonical">
    <header><h1>Wrong</h1></header><article><h1>Selected</h1>
    <span class="byline">Local</span><time datetime="2024-01-02">January</time><p>Text.</p></article></html>`,
    { url: "https://example.org/source" },
  );
  assert.deepEqual(result.metadata, {
    title: "Selected",
    author: "Explicit",
    description: "Description",
    language: "ja",
    publishedTime: "2024-01-02",
    url: "https://example.org/source",
    canonicalUrl: "https://example.org/canonical",
  });
});

test("JSON-LD arrays, graphs, and explicit metadata survive cleanup", () => {
  const article = {
    "@type": ["Thing", "NewsArticle"],
    headline: "Headline",
    author: [{ name: "A" }, { name: "B" }],
    datePublished: "Yesterday",
    inLanguage: "fr",
  };
  for (const wrapper of [article, [article], { "@graph": [article] }]) {
    const result = extract(
      `<script type="application/ld+json">${JSON.stringify(wrapper)}</script>`,
    );
    assert.equal(result.markdown, "");
    assert.equal(result.metadata.title, "Headline");
    assert.equal(result.metadata.author, "A, B");
    assert.equal(result.metadata.publishedTime, "Yesterday");
    assert.equal(result.metadata.language, "fr");
  }
  for (const content of ["{invalid", "null", "42", '{"@type":"Product","name":"Wrong"}']) {
    assert.equal(
      extract(`<script type="application/ld+json">${content}</script>`).metadata.title,
      null,
    );
  }
});

test("literal code preserves nested text and whitespace", () => {
  const html =
    '<article><p><code><b>x</b> &amp; <i>y</i></code></p><pre><code class="language-python"><span>if x:</span>\n  print(&quot;tea&quot;)</code></pre></article>';
  assert.equal(convert(html), '`x & y`\n\n```python\nif x:\n  print("tea")\n```\n');
});

test("empty metadata uses null", () => {
  assert.ok(Object.values(extract("").metadata).every((value) => value === null));
});
