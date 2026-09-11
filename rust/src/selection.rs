use crate::{
    Diagnostics, Strategy,
    tree::{Id, Node, Tree, has},
};
use std::collections::{HashMap, HashSet};
const INERT: &str = "head title meta link base script style template noscript iframe object embed svg canvas nav button input select textarea dialog";
const NEGATIVE: &str = "advertisement ads advert promo promotion related share sharing social cookie consent newsletter comments comment sidebar breadcrumb breadcrumbs pagination toolbar footer banner dropdown catlinks menu pager teaser toc well";
const POSITIVE: &str = "article content main post entry story text documentation";
const REFERENCES: &str = "footnotes references endnotes bibliography";
const CONTAINERS: &str = "article main section div body #document";
const EVIDENCE: &str = "p pre li dt dd td th blockquote";
const STRUCTURES: &str = "ul ol dl table blockquote pre";
pub const HEADINGS: &str = "h1 h2 h3 h4 h5 h6";
fn hints(n: &Node) -> HashSet<String> {
    let value = format!("{} {}", n.attr("class"), n.attr("id"));
    let mut expanded = String::new();
    let mut previous = ' ';
    for c in value.chars() {
        if previous.is_ascii_lowercase() && c.is_ascii_uppercase() {
            expanded.push(' ');
        }
        expanded.push(c);
        previous = c;
    }
    expanded
        .to_lowercase()
        .split(|c: char| !c.is_ascii_lowercase() && !c.is_ascii_digit())
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
        .collect()
}
fn intersects(tokens: &HashSet<String>, words: &str) -> bool {
    words.split_ascii_whitespace().any(|w| tokens.contains(w))
}
#[derive(Clone, Copy, Default)]
struct Stats {
    characters: usize,
    linked: usize,
    punctuation: usize,
    blocks: usize,
    headings: usize,
    code: usize,
    cells: usize,
    images: usize,
    controls: usize,
}
impl Stats {
    fn density(self) -> f64 {
        self.linked as f64 / self.characters.max(1) as f64
    }
}
fn hidden_style(style: &str) -> bool {
    style.split(';').any(|declaration| {
        let Some((key, value)) = declaration.split_once(':') else {
            return false;
        };
        let key = key.trim().to_ascii_lowercase();
        let lower = value.to_ascii_lowercase();
        let value = lower
            .trim()
            .strip_suffix("!important")
            .unwrap_or(lower.trim())
            .trim();
        key == "display" && value == "none"
            || key == "visibility" && matches!(value, "hidden" | "collapse")
    })
}
fn excluded(n: &Node, local: bool) -> bool {
    if has(INERT, &n.tag)
        || n.attrs.contains_key("hidden")
        || n.attr("aria-hidden").eq_ignore_ascii_case("true")
        || hidden_style(n.attr("style"))
    {
        return true;
    }
    if n.tag == "a" && hints(n).contains("headerlink") {
        return n.attr("href").starts_with('#');
    }
    if has(
        "navigation banner contentinfo menu menubar dialog",
        &n.attr("role").to_lowercase(),
    ) {
        return true;
    }
    has("header footer", &n.tag) && !local
}
fn visible(tree: &mut Tree) {
    let mut stack = vec![(0, false)];
    while let Some((id, local)) = stack.pop() {
        let n = &tree.nodes[id];
        let local = local || has("article main", &n.tag) || n.attr("role") == "main";
        let mut kept = Vec::new();
        for &c in &n.children {
            if !tree.nodes[c].tag.is_empty() {
                if excluded(&tree.nodes[c], local) {
                    continue;
                }
                stack.push((c, local));
            }
            kept.push(c);
        }
        tree.nodes[id].children = kept;
    }
}
fn statistics(tree: &Tree) -> Vec<Stats> {
    let mut result = vec![Stats::default(); tree.nodes.len()];
    for id in tree.walk(0).into_iter().rev() {
        let n = &tree.nodes[id];
        let mut s = Stats::default();
        for &c in &n.children {
            let child = &tree.nodes[c];
            if child.tag.is_empty() {
                s.characters += child.text.trim().chars().count();
                s.punctuation += child
                    .text
                    .chars()
                    .filter(|&c| ",.;:!?。，；：！？،؛".contains(c))
                    .count();
            } else {
                let o = result[c];
                s.characters += o.characters;
                s.linked += o.linked;
                s.punctuation += o.punctuation;
                s.blocks += o.blocks;
                s.headings += o.headings;
                s.code += o.code;
                s.cells += o.cells;
                s.images += o.images;
                s.controls += o.controls;
            }
        }
        s.blocks += usize::from(has(EVIDENCE, &n.tag) && s.characters > 0);
        s.headings += usize::from(has(HEADINGS, &n.tag) && s.characters > 0);
        s.code += usize::from(n.tag == "pre");
        s.cells += usize::from(has("td th", &n.tag));
        s.images += usize::from(n.tag == "img" && !n.attr("src").is_empty());
        s.controls += usize::from(has("form button input select textarea", &n.tag));
        if n.tag == "a" {
            s.linked = s.characters;
        }
        result[id] = s;
    }
    result
}
fn clutter(tree: &Tree, id: Id, s: Stats) -> bool {
    let n = &tree.nodes[id];
    if has("#document html body main article", &n.tag) {
        return false;
    }
    let tokens = hints(n);
    if intersects(&tokens, REFERENCES) || n.attr("role") == "note" {
        return false;
    }
    if !intersects(&tokens, NEGATIVE) || has(EVIDENCE, &n.tag) || has(HEADINGS, &n.tag) {
        return false;
    }
    if s.density() > 0.35
        || s.controls > 0
        || tokens.contains("footer") && s.density() > 0.15
        || n.tag == "aside" && s.code == 0 && s.cells == 0
        || s.blocks == 0 && s.characters < 180
    {
        return true;
    }
    if intersects(&tokens, "comments comment") {
        return tree
            .elements(id)
            .iter()
            .filter(|&&c| intersects(&hints(&tree.nodes[c]), "comment reply"))
            .count()
            >= 2;
    }
    false
}
fn plausible(n: &Node, s: Stats, semantic: bool) -> bool {
    if s.characters == 0 {
        return semantic && s.images > 0;
    }
    if s.code > 0 || s.cells > 0 || n.tag == "p" && s.characters > s.linked {
        return true;
    }
    if s.density() >= 0.8 {
        return semantic && s.headings > 0 && s.blocks > 0;
    }
    has(CONTAINERS, &n.tag)
        || has(EVIDENCE, &n.tag)
        || has(HEADINGS, &n.tag)
        || has(STRUCTURES, &n.tag)
        || semantic
}
fn scores(tree: &Tree, stats: &[Stats], relaxed: bool) -> HashMap<Id, f64> {
    let mut result = HashMap::new();
    for id in tree.walk(0) {
        let n = &tree.nodes[id];
        let s = stats[id];
        if !has(CONTAINERS, &n.tag) || !plausible(n, s, false) {
            continue;
        }
        let tokens = hints(n);
        let mut score = (s.characters as f64).sqrt() + s.blocks.min(30) as f64 * 2.0;
        score += s.punctuation.min(40) as f64 * 0.25 + (s.code + s.cells).min(12) as f64 * 2.0;
        if intersects(&tokens, POSITIVE) {
            score += 8.0;
        }
        if !relaxed && intersects(&tokens, NEGATIVE) {
            score -= 18.0;
        }
        result.insert(id, score * (1.0 - s.density()).powi(2));
    }
    for id in tree.walk(0) {
        let n = &tree.nodes[id];
        if !has(EVIDENCE, &n.tag)
            || tree
                .elements(id)
                .iter()
                .any(|&c| has(EVIDENCE, &tree.nodes[c].tag))
        {
            continue;
        }
        let s = stats[id];
        let support = (1.0 + (s.characters as f64 / 100.0).min(3.0)) * (1.0 - s.density());
        let mut ancestor = n.parent;
        for weight in [1.0, 0.5, 0.25] {
            let Some(a) = ancestor else {
                break;
            };
            if let Some(score) = result.get_mut(&a) {
                *score += support * weight;
            }
            ancestor = tree.nodes[a].parent;
        }
    }
    result
}
fn score(ranked: &HashMap<Id, f64>, id: Id) -> f64 {
    ranked.get(&id).copied().unwrap_or(0.0)
}
fn winner(nodes: &[Id], ranked: &HashMap<Id, f64>) -> Option<Id> {
    let mut best = None;
    for &id in nodes {
        if best.is_none_or(|b| score(ranked, id) > score(ranked, b)) {
            best = Some(id);
        }
    }
    best
}
fn candidates(tree: &Tree, ranked: &HashMap<Id, f64>) -> Vec<Id> {
    tree.walk(0)
        .into_iter()
        .filter(|id| ranked.contains_key(id) && !has("body #document", &tree.nodes[*id].tag))
        .collect()
}
pub fn select(tree: &mut Tree) -> (Vec<Id>, Diagnostics) {
    visible(tree);
    let mut stats = statistics(tree);
    let mut removed = 0;
    let mut stack = vec![0];
    while let Some(id) = stack.pop() {
        let mut kept = Vec::new();
        for &c in &tree.nodes[id].children {
            if !tree.nodes[c].tag.is_empty() && clutter(tree, c, stats[c]) {
                removed += 1;
            } else {
                kept.push(c);
            }
        }
        stack.extend(
            kept.iter()
                .rev()
                .filter(|&&c| !tree.nodes[c].tag.is_empty())
                .copied(),
        );
        tree.nodes[id].children = kept;
    }
    if removed > 0 {
        stats = statistics(tree);
    }
    let mut ranked = scores(tree, &stats, false);
    let mut notes = Vec::new();
    if removed > 0 {
        notes.push(format!(
            "Removed {removed} conditionally identified clutter blocks."
        ));
    }
    let mut semantic = Vec::new();
    let mut landmarks = Vec::new();
    for id in tree.walk(0) {
        let n = &tree.nodes[id];
        let landmark = n.tag == "main" || n.attr("role") == "main";
        if !(landmark || n.tag == "article")
            || !plausible(n, stats[id], true)
            || clutter(tree, id, stats[id])
            || hints(n).contains("teaser") && stats[id].density() > 0.1
        {
            continue;
        }
        semantic.push(id);
        if landmark {
            landmarks.push(id);
        }
    }
    if !landmarks.is_empty() {
        semantic = landmarks;
    }
    if let Some(best) = winner(&semantic, &ranked) {
        return (
            vec![best],
            Diagnostics {
                strategy: Strategy::Semantic,
                notes,
            },
        );
    }
    let mut best = winner(&candidates(tree, &ranked), &ranked);
    if best.is_none_or(|b| score(&ranked, b) < 5.0) {
        notes.push("Retried selection once with relaxed class penalties.".into());
        ranked = scores(tree, &stats, true);
        best = winner(&candidates(tree, &ranked), &ranked);
    }
    if let Some(best) = best.filter(|&b| score(&ranked, b) >= 5.0) {
        let mut selected = vec![best];
        if let Some(parent) = tree.nodes[best].parent {
            let threshold = (score(&ranked, best) * 0.18).max(5.0);
            selected = tree
                .elements(parent)
                .into_iter()
                .filter(|&id| {
                    let n = &tree.nodes[id];
                    let s = stats[id];
                    !clutter(tree, id, s)
                        && (id == best
                            || score(&ranked, id) >= threshold && s.density() < 0.5
                            || has(HEADINGS, &n.tag) && s.density() < 0.5
                            || n.tag == "p" && s.density() < 0.25 && s.characters > 0)
                })
                .collect();
        }
        return (
            selected,
            Diagnostics {
                strategy: Strategy::Scored,
                notes,
            },
        );
    }
    let mut selected = Vec::new();
    let mut stack = vec![0];
    while selected.len() < 256 {
        let Some(id) = stack.pop() else {
            break;
        };
        let n = &tree.nodes[id];
        let s = stats[id];
        if clutter(tree, id, s) {
            continue;
        }
        let children = tree.elements(id);
        if (has(EVIDENCE, &n.tag) || has(HEADINGS, &n.tag) || has(STRUCTURES, &n.tag))
            && plausible(n, s, false)
            || children.is_empty() && s.characters > 0 && s.density() < 0.5
        {
            selected.push(id);
        } else {
            stack.extend(children.into_iter().rev());
        }
    }
    notes.push(
        if selected.is_empty() {
            "No relevant visible content found."
        } else {
            "Recovered plausible blocks."
        }
        .into(),
    );
    (
        selected,
        Diagnostics {
            strategy: Strategy::Fallback,
            notes,
        },
    )
}
