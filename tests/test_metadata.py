import json

import pytest

from htomd import extract


def test_title_precedence_and_local_metadata() -> None:
    html = """<html lang="ja"><head><title>Document</title>
    <meta property="og:title" content="Open Graph"><meta name="description" content="Description">
    <link rel="canonical" href="/canonical"></head><body>
    <header><h1>Site title</h1><span class="byline">Wrong</span></header>
    <article><h1>Selected title</h1><span class="byline">Author</span>
    <time datetime="2024-01-02">January</time><p>Article text.</p></article></body></html>"""
    metadata = extract(html, url="https://example.org/source").metadata
    assert metadata.title == "Selected title"
    assert metadata.author == "Author"
    assert metadata.description == "Description"
    assert metadata.language == "ja"
    assert metadata.published_time == "2024-01-02"
    assert metadata.url == "https://example.org/source"
    assert metadata.canonical_url == "https://example.org/canonical"


@pytest.mark.parametrize("wrapper", ["object", "array", "graph"])
def test_article_jsonld(wrapper: str) -> None:
    article: object = {
        "@type": ["Thing", "NewsArticle"],
        "headline": "Headline",
        "author": [{"name": "A"}, {"name": "B"}],
        "datePublished": "Yesterday",
        "description": "Summary",
        "inLanguage": "fr",
    }
    if wrapper == "array":
        article = [{"@type": "WebSite", "name": "Wrong"}, article]
    elif wrapper == "graph":
        article = {"@graph": [{"@type": "WebSite", "name": "Wrong"}, article]}
    result = extract(f'<script type="application/ld+json">{json.dumps(article)}</script>')
    assert result.markdown == ""
    assert result.metadata.title == "Headline"
    assert result.metadata.author == "A, B"
    assert result.metadata.published_time == "Yesterday"
    assert result.metadata.language == "fr"


def test_explicit_author_and_date_take_precedence() -> None:
    html = """<meta name="author" content="Explicit">
    <meta property="article:published_time" content="Exact date">
    <script type="application/ld+json">
    {"@type":"Article","author":"JSON","datePublished":"JSON date"}</script>
    <article><p class="byline">Local</p>
    <time datetime="Local date">Today</time><p>Text</p></article>"""
    metadata = extract(html).metadata
    assert metadata.author == "Explicit"
    assert metadata.published_time == "Exact date"


@pytest.mark.parametrize(
    "content",
    [
        "{invalid",
        '{"@type":"Product","name":"Wrong"}',
        '{"applicationState":{"title":"Wrong"}}',
        "null",
        "42",
    ],
)
def test_ignore_unqualified_json(content: str) -> None:
    metadata = extract(f'<script type="application/ld+json">{content}</script>').metadata
    assert metadata.title is None
    assert metadata.author is None


def test_metadata_survives_empty_selection() -> None:
    result = extract('<title>Title</title><meta name="author" content="A"><nav>Navigation</nav>')
    assert result.markdown == ""
    assert result.metadata.title == "Title"
    assert result.metadata.author == "A"


def test_open_graph_before_document_title() -> None:
    assert (
        extract('<title>Document</title><meta property="og:title" content="OG">').metadata.title
        == "OG"
    )


def test_modified_time_is_not_publication_time() -> None:
    metadata = extract(
        '<article><p>Text</p><time itemprop="dateModified" datetime="Now">Now</time></article>'
    ).metadata
    assert metadata.published_time is None


def test_unsafe_canonical_is_omitted() -> None:
    assert (
        extract('<link rel="canonical" href="javascript:alert(1)">').metadata.canonical_url is None
    )


def test_missing_fields_are_none() -> None:
    metadata = extract("").metadata
    assert all(getattr(metadata, key) is None for key in metadata.__slots__)
