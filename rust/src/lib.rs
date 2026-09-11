//! Extract Markdown and metadata from decoded HTML without network access.
//!
//! ```
//! let document = htomd::extract("<h1>Tea</h1>", htomd::Options::default());
//! assert_eq!(document.markdown, "# Tea\n");
//! ```
mod entities;
mod metadata;
mod parser;
mod render;
mod selection;
mod tree;
mod urls;

use serde::Serialize;

/// Optional source context. `Some("")` differs from an omitted URL.
#[derive(Clone, Copy, Debug, Default)]
pub struct Options<'a> {
    pub url: Option<&'a str>,
}
/// Explicit metadata; absent values serialize as null.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize)]
pub struct Metadata {
    pub title: Option<String>,
    pub author: Option<String>,
    pub description: Option<String>,
    pub language: Option<String>,
    pub published_time: Option<String>,
    pub url: Option<String>,
    pub canonical_url: Option<String>,
}
/// How relevant content was selected.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Strategy {
    Semantic,
    Scored,
    Fallback,
    None,
}
/// Selection and recovery explanations.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Diagnostics {
    pub strategy: Strategy,
    pub notes: Vec<String>,
}
/// Owned results, independent of the input and of other calls.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Document {
    pub markdown: String,
    pub metadata: Metadata,
    pub diagnostics: Diagnostics,
}
/// Recover malformed HTML best-effort and extract its relevant content.
pub fn extract(html: &str, options: Options<'_>) -> Document {
    let (mut tree, mut notes) = parser::parse(html);
    let base = urls::document_base(&tree, options.url);
    let mut metadata = metadata::read(&tree, options.url, base.as_deref());
    let (selected, mut diagnostics) = selection::select(&mut tree);
    metadata::refine(&tree, &selected, &mut metadata);
    let markdown = render::render(&tree, &selected, base.as_deref());
    notes.append(&mut diagnostics.notes);
    diagnostics.notes = notes;
    if markdown.is_empty() {
        diagnostics.strategy = Strategy::None;
    }
    Document {
        markdown,
        metadata,
        diagnostics,
    }
}
/// Return the Markdown produced by [`extract`].
pub fn convert(html: &str, options: Options<'_>) -> String {
    extract(html, options).markdown
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn owned_optional_values() {
        let mut document = extract("<h1>Tea</h1>", Options { url: Some("") });
        assert_eq!(document.metadata.url.as_deref(), Some(""));
        document.metadata.title = Some("Changed".into());
        document.diagnostics.notes.push("Changed".into());
        let next = extract("<h1>Tea</h1>", Options::default());
        assert_eq!(next.metadata.title.as_deref(), Some("Tea"));
        assert_eq!(next.metadata.url, None);
    }
    #[test]
    fn deep_pipeline_and_drop() {
        let html = format!(
            "<article>{}Text.{}</article>",
            "<div>".repeat(3000),
            "</div>".repeat(3000)
        );
        assert_eq!(convert(&html, Options::default()), "Text.\n");
    }
    #[test]
    fn large_and_negative_counters() {
        for (start, expected) in [
            (
                "999999999999999999999999999",
                "999999999999999999999999999. A\n1000000000000000000000000000. B\n",
            ),
            ("-1", "-1. A\n0. B\n"),
        ] {
            assert_eq!(
                convert(
                    &format!("<ol start='{start}'><li>A<li>B</ol>"),
                    Options::default()
                ),
                expected
            );
        }
    }
    #[test]
    fn metadata_precedence() {
        let d = extract(
            r#"<meta property="og:title" content="Social"><meta name="author" content="First"><meta name="author" content="Second"><article><h1>Chosen</h1><time datetime="Today">Date</time><p>Tea</p></article>"#,
            Options::default(),
        );
        assert_eq!(d.metadata.title.as_deref(), Some("Chosen"));
        assert_eq!(d.metadata.author.as_deref(), Some("First"));
        assert_eq!(d.metadata.published_time.as_deref(), Some("Today"));
    }
}
