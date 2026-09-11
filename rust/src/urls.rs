use crate::tree::{Tree, has};
use url::Url;
fn checked(value: &str) -> String {
    value
        .chars()
        .filter(|&c| c > ' ' && c != '\u{7f}')
        .collect()
}
fn scheme(value: &str) -> &str {
    if let Some((prefix, _)) = value.split_once(':')
        && prefix
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphabetic)
        && prefix
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"+.-".contains(&c))
    {
        return prefix;
    }
    ""
}
fn allowed(value: &str) -> bool {
    let normalized = checked(value);
    let scheme = scheme(&normalized).to_ascii_lowercase();
    scheme.is_empty() || has("http https mailto tel ftp", &scheme)
}
pub fn safe(value: &str, base: Option<&str>) -> Option<String> {
    let value = value.trim();
    if !allowed(value) {
        return None;
    }
    // Preserve supplied spelling of absolute references after validation.
    if !scheme(&checked(value)).is_empty() {
        Url::parse(&checked(value)).ok()?;
        return Some(value.to_owned());
    }
    if let Some(base) = base.filter(|b| !b.is_empty()) {
        let joined = Url::parse(base).ok()?.join(value).ok()?.to_string();
        if !allowed(&joined) {
            return None;
        }
        return Some(joined);
    }
    Some(value.to_owned())
}
pub fn document_base(tree: &Tree, source: Option<&str>) -> Option<String> {
    let base = source.filter(|s| !s.is_empty()).and_then(|s| safe(s, None));
    for id in tree.walk(0) {
        let n = &tree.nodes[id];
        if n.tag != "base" || !n.attrs.contains_key("href") {
            continue;
        }
        if let Some(candidate) = safe(n.attr("href"), base.as_deref())
            && let Ok(url) = Url::parse(&candidate)
            && matches!(url.scheme(), "http" | "https")
            && url.host_str().is_some()
        {
            return Some(candidate);
        }
    }
    base
}
pub fn destination(value: &str) -> String {
    let mut out = String::new();
    for c in value.bytes() {
        if c.is_ascii_alphanumeric() || b"/:?#@!$&'*+,;=%[]~_-.".contains(&c) {
            out.push(c as char);
        } else {
            use std::fmt::Write;
            write!(out, "%{c:02X}").expect("writing to String");
        }
    }
    out
}
