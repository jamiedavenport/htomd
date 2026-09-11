use crate::{
    Metadata,
    tree::{Id, Tree, has},
    urls,
};
use serde_json::Value;
use std::collections::HashMap;
const ARTICLE_TYPES: &str = "Article NewsArticle BlogPosting TechArticle ScholarlyArticle MedicalScholarlyArticle Report AnalysisNewsArticle OpinionNewsArticle ReviewNewsArticle BackgroundNewsArticle APIReference LiveBlogPosting";
fn string(v: &Value) -> Option<String> {
    v.as_str().and_then(optional)
}
fn optional(s: &str) -> Option<String> {
    let s = s.trim();
    if s.is_empty() { None } else { Some(s.into()) }
}
fn author_name(value: &Value) -> Option<String> {
    match value {
        Value::String(s) => optional(s),
        Value::Object(_) => string(&value["name"]),
        Value::Array(values) => optional(
            &values
                .iter()
                .filter_map(author_name)
                .collect::<Vec<_>>()
                .join(", "),
        ),
        _ => None,
    }
}
fn article(tree: &Tree, id: Id) -> Value {
    if !tree.nodes[id]
        .attr("type")
        .eq_ignore_ascii_case("application/ld+json")
    {
        return Value::Null;
    }
    let Ok(value) = serde_json::from_str::<Value>(&tree.text(id, false)) else {
        return Value::Null;
    };
    let mut stack = vec![&value];
    while let Some(item) = stack.pop() {
        match item {
            Value::Array(items) => stack.extend(items.iter().rev()),
            Value::Object(map) => {
                let kind = &item["@type"];
                let kinds = if let Value::Array(kinds) = kind {
                    kinds.iter().collect::<Vec<_>>()
                } else {
                    vec![kind]
                };
                if kinds.iter().any(|k| {
                    k.as_str()
                        .is_some_and(|s| has(ARTICLE_TYPES, s.rsplit('/').next().unwrap_or(s)))
                }) {
                    return item.clone();
                }
                if let Some(graph) = map.get("@graph")
                    && (graph.is_object() || graph.is_array())
                {
                    stack.push(graph);
                }
            }
            _ => {}
        }
    }
    Value::Null
}
pub fn read(tree: &Tree, source: Option<&str>, base: Option<&str>) -> Metadata {
    let mut fields = HashMap::new();
    let mut json = Value::Null;
    let mut title = None;
    let mut language = None;
    let mut canonical = None;
    for id in tree.walk(0) {
        let n = &tree.nodes[id];
        match n.tag.as_str() {
            "meta" => {
                let key = n
                    .attrs
                    .get("property")
                    .map(String::as_str)
                    .unwrap_or(n.attr("name"))
                    .to_lowercase();
                if let Some(content) = optional(n.attr("content")) {
                    fields.entry(key).or_insert(content);
                }
            }
            "title" if title.is_none() => title = optional(&tree.text(id, true)),
            "html" => language = optional(n.attr("lang")).or_else(|| optional(n.attr("xml:lang"))),
            "link" if has(&n.attr("rel").to_lowercase(), "canonical") && canonical.is_none() => {
                canonical = urls::safe(n.attr("href"), base).filter(|s| !s.is_empty())
            }
            "script" if json.is_null() => {
                json = article(tree, id);
            }
            _ => {}
        }
    }
    Metadata {
        title: fields
            .get("og:title")
            .cloned()
            .or(title)
            .or_else(|| string(&json["headline"])),
        author: fields
            .get("author")
            .cloned()
            .or_else(|| author_name(&json["author"])),
        description: fields
            .get("description")
            .or_else(|| fields.get("og:description"))
            .cloned()
            .or_else(|| string(&json["description"])),
        language: language
            .or_else(|| string(&json["inLanguage"]))
            .or_else(|| fields.get("og:locale").cloned()),
        published_time: fields
            .get("article:published_time")
            .or_else(|| fields.get("date"))
            .cloned()
            .or_else(|| string(&json["datePublished"])),
        url: source.map(str::to_owned),
        canonical_url: canonical,
    }
}
pub fn refine(tree: &Tree, selected: &[Id], metadata: &mut Metadata) {
    let mut heading = None;
    for &root in selected {
        for id in tree.walk(root) {
            let n = &tree.nodes[id];
            if n.tag == "h1" && heading.is_none() {
                heading = optional(&tree.text(id, true));
            }
            if metadata.author.is_none()
                && (n.attr("itemprop") == "author"
                    || has(n.attr("rel"), "author")
                    || n.attr("class")
                        .to_lowercase()
                        .split_whitespace()
                        .any(|t| has("byline author p-author", t)))
            {
                metadata.author = optional(&tree.text(id, true));
            }
            if metadata.published_time.is_none()
                && n.tag == "time"
                && n.attr("itemprop") != "dateModified"
            {
                metadata.published_time =
                    optional(n.attr("datetime")).or_else(|| optional(&tree.text(id, true)));
            }
        }
    }
    if heading.is_some() {
        metadata.title = heading;
    }
}
