use crate::{
    selection::HEADINGS,
    tree::{Id, Tree, has, normalize},
    urls,
};
use std::collections::HashMap;
const LITERAL: &str = "pre code kbd samp";
const BLOCKS: &str =
    "p div article main section header footer figure figcaption address details summary dl";
fn block_neighbor(tag: &str) -> bool {
    has(BLOCKS, tag) || has(HEADINGS, tag) || has("ul ol pre table blockquote hr li", tag)
}
fn escape(value: &str) -> String {
    let mut escaped = String::new();
    for c in value.chars() {
        match c {
            '&' => escaped.push_str("&amp;"),
            '<' => escaped.push_str("&lt;"),
            '>' => escaped.push_str("&gt;"),
            '\\' | '`' | '*' | '_' | '~' | '[' | ']' => {
                escaped.push('\\');
                escaped.push(c);
            }
            _ => escaped.push(c),
        }
    }
    escaped
        .split('\n')
        .map(|line| {
            let body = line.trim_start();
            let bytes = body.as_bytes();
            let Some(&first) = bytes.first() else {
                return line.into();
            };
            let mut length = 0;
            let mut numeric = false;
            if first == b'#' {
                length = bytes.iter().take_while(|&&b| b == b'#').count();
                if length > 6 {
                    length = 0;
                }
            } else if first == b'-' || first == b'+' {
                length = 1;
            }
            if first.is_ascii_digit() {
                let digits = bytes.iter().take_while(|b| b.is_ascii_digit()).count();
                if matches!(bytes.get(digits), Some(b'.' | b')')) {
                    length = digits + 1;
                    numeric = true;
                }
            }
            let run = bytes.iter().take_while(|&&b| b == first).count();
            let horizontal = b"=~-".contains(&first) && run >= 3;
            if horizontal {
                length = run;
            }
            if length == 0
                || !body[length..]
                    .chars()
                    .next()
                    .is_some_and(char::is_whitespace)
                    && !(horizontal && length == body.len())
            {
                return line.into();
            }
            let prefix = &line[..line.len() - body.len()];
            if numeric {
                format!(
                    "{prefix}{}\\{}{}",
                    &body[..length - 1],
                    &body[length - 1..length],
                    &body[length..]
                )
            } else {
                format!("{prefix}\\{body}")
            }
        })
        .collect::<Vec<String>>()
        .join("\n")
}
fn longest_run(s: &str, c: char) -> usize {
    let mut longest = 0;
    let mut current = 0;
    for ch in s.chars() {
        if ch == c {
            current += 1;
            longest = longest.max(current);
        } else {
            current = 0;
        }
    }
    longest
}
fn inline_code(tree: &Tree, id: Id) -> String {
    let value = tree
        .text(id, false)
        .replace("\r\n", " ")
        .replace(['\r', '\n'], " ");
    if value.is_empty() {
        return value;
    }
    let delimiter = "`".repeat(longest_run(&value, '`') + 1);
    let padding = if value.starts_with('`')
        || value.ends_with('`')
        || value.starts_with(' ') && value.ends_with(' ') && !value.trim().is_empty()
    {
        " "
    } else {
        ""
    };
    format!("{delimiter}{padding}{value}{padding}{delimiter}")
}
fn valid_language(s: &str) -> bool {
    !s.is_empty()
        && s.chars()
            .all(|c| c.is_alphanumeric() || "_.+#-".contains(c))
}
fn code_language(tree: &Tree, id: Id) -> String {
    let mut candidates = vec![id];
    candidates.extend(tree.elements(id));
    candidates.extend(tree.nodes[id].parent);
    for id in candidates {
        let n = &tree.nodes[id];
        for token in n.attr("class").split_whitespace() {
            if (token.starts_with("language-")
                || token.starts_with("lang-")
                || token.starts_with("highlight-"))
                && let Some((_, value)) = token.split_once('-')
                && valid_language(value)
            {
                return value.into();
            }
        }
        let value = n.attr("data-language");
        if valid_language(value) {
            return value.into();
        }
    }
    String::new()
}
fn fenced_code(tree: &Tree, id: Id) -> String {
    let value = tree
        .text(id, false)
        .replace("\r\n", "\n")
        .replace('\r', "\n");
    let fence = "`".repeat(3.max(longest_run(&value, '`') + 1));
    let ending = if value.ends_with('\n') { "" } else { "\n" };
    format!(
        "\n\n{fence}{}\n{value}{ending}{fence}\n\n",
        code_language(tree, id)
    )
}
fn join_parts(parts: Vec<String>) -> String {
    let mut result: Vec<String> = Vec::new();
    for mut part in parts {
        if part.is_empty() {
            continue;
        }
        if let Some(last) = result.last_mut()
            && last.ends_with('\n')
            && part.starts_with('\n')
        {
            last.truncate(last.trim_end_matches('\n').len());
            part = format!("\n\n{}", part.trim_start_matches('\n'));
        }
        result.push(part);
    }
    result.concat()
}
fn wrap_inline(body: &str, marker: &str) -> String {
    let content = body.trim();
    if content.is_empty() {
        return body.into();
    }
    let leading = if body.starts_with(char::is_whitespace) {
        " "
    } else {
        ""
    };
    let trailing = if body.ends_with(char::is_whitespace) {
        " "
    } else {
        ""
    };
    format!("{leading}{marker}{content}{marker}{trailing}")
}
// Only decimal parsing and increment are needed for list counters, including negatives.
struct Counter {
    negative: bool,
    digits: Vec<u8>,
}
impl Counter {
    fn parse(value: &str) -> Option<Self> {
        let value = value.trim();
        let negative = value.starts_with('-');
        let value = value.strip_prefix(['-', '+']).unwrap_or(value);
        if value.is_empty() || !value.bytes().all(|c| c.is_ascii_digit()) {
            return None;
        }
        let digits = value.trim_start_matches('0');
        let digits = if digits.is_empty() { "0" } else { digits };
        Some(Self {
            negative: negative && digits != "0",
            digits: digits.bytes().map(|c| c - b'0').collect(),
        })
    }
    fn increment(&mut self) {
        if self.negative {
            for d in self.digits.iter_mut().rev() {
                if *d > 0 {
                    *d -= 1;
                    break;
                }
                *d = 9;
            }
            while self.digits.len() > 1 && self.digits[0] == 0 {
                self.digits.remove(0);
            }
            if self.digits == [0] {
                self.negative = false;
            }
        } else {
            for d in self.digits.iter_mut().rev() {
                if *d < 9 {
                    *d += 1;
                    return;
                }
                *d = 0;
            }
            self.digits.insert(0, 1);
        }
    }
    fn text(&self) -> String {
        let mut out = if self.negative {
            "-".into()
        } else {
            String::new()
        };
        out.extend(self.digits.iter().map(|d| (d + b'0') as char));
        out
    }
}
fn render_list(tree: &Tree, id: Id, rendered: &HashMap<Id, String>) -> String {
    let n = &tree.nodes[id];
    let mut number = Counter::parse(n.attr("start")).unwrap_or(Counter {
        negative: false,
        digits: vec![1],
    });
    let mut items = Vec::new();
    for child in tree.elements(id) {
        let c = &tree.nodes[child];
        if c.tag != "li" {
            continue;
        }
        let value = c.attr("value");
        let digits = value.strip_prefix('-').unwrap_or(value);
        if n.tag == "ol"
            && (1..=9).contains(&digits.len())
            && digits.bytes().all(|c| c.is_ascii_digit())
            && let Some(parsed) = Counter::parse(value)
        {
            number = parsed;
        }
        let marker = if n.tag == "ol" {
            format!("{}. ", number.text())
        } else {
            "- ".into()
        };
        let body = rendered[&child].trim();
        if !body.is_empty() {
            let lines = body
                .lines()
                .enumerate()
                .map(|(i, line)| {
                    if i == 0 {
                        format!("{marker}{line}")
                    } else if line.is_empty() {
                        String::new()
                    } else {
                        format!("{}{line}", " ".repeat(marker.len()))
                    }
                })
                .collect::<Vec<_>>();
            items.push(lines.join("\n"));
        }
        number.increment();
    }
    if items.is_empty() {
        String::new()
    } else {
        format!("\n{}\n", items.join("\n"))
    }
}
fn table_rows(tree: &Tree, id: Id) -> Vec<Id> {
    let mut rows = Vec::new();
    let mut stack = tree.elements(id);
    stack.reverse();
    while let Some(c) = stack.pop() {
        let tag = &tree.nodes[c].tag;
        if tag == "tr" {
            rows.push(c);
        } else if has("thead tbody tfoot", tag) {
            stack.extend(tree.elements(c).into_iter().rev());
        }
    }
    rows
}
fn render_table(tree: &Tree, id: Id, rendered: &HashMap<Id, String>) -> String {
    let rows = table_rows(tree, id)
        .into_iter()
        .map(|r| {
            tree.elements(r)
                .into_iter()
                .filter(|&c| has("th td", &tree.nodes[c].tag))
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let mut captions = tree
        .elements(id)
        .into_iter()
        .filter(|&c| tree.nodes[c].tag == "caption")
        .map(|c| rendered[&c].trim().to_owned())
        .collect::<Vec<_>>();
    let simple = !rows.is_empty()
        && !rows[0].is_empty()
        && rows.iter().all(|row| {
            row.len() == rows[0].len()
                && row.iter().all(|&c| {
                    let n = &tree.nodes[c];
                    ["colspan", "rowspan"]
                        .iter()
                        .all(|key| n.attrs.get(*key).is_none_or(|v| v == "1"))
                        && !tree
                            .elements(c)
                            .iter()
                            .any(|&child| has("table pre ul ol p", &tree.nodes[child].tag))
                })
        });
    let lines = if !simple {
        rows.iter()
            .enumerate()
            .map(|(i, row)| {
                format!(
                    "{}. {}",
                    i + 1,
                    row.iter()
                        .map(|c| rendered[c].trim().replace('\n', " "))
                        .collect::<Vec<_>>()
                        .join(" — ")
                )
            })
            .collect::<Vec<_>>()
    } else {
        let mut values = rows
            .iter()
            .map(|row| {
                row.iter()
                    .map(|c| rendered[c].trim().replace('|', "\\|").replace('\n', " "))
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        if !rows[0].iter().any(|&c| tree.nodes[c].tag == "th") {
            values.insert(0, vec![String::new(); rows[0].len()]);
        }
        values.insert(1, vec!["---".into(); rows[0].len()]);
        values
            .iter()
            .map(|row| format!("| {} |", row.join(" | ")))
            .collect::<Vec<_>>()
    };
    captions.push(lines.join("\n"));
    format!("\n\n{}\n\n", captions.join("\n\n"))
}
fn serialize(
    tree: &Tree,
    id: Id,
    body: &str,
    rendered: &HashMap<Id, String>,
    base: Option<&str>,
) -> String {
    let n = &tree.nodes[id];
    let tag = n.tag.as_str();
    let trimmed = body.trim();
    if has(HEADINGS, tag) {
        return if trimmed.is_empty() {
            String::new()
        } else {
            format!(
                "\n\n{} {trimmed}\n\n",
                "#".repeat((tag.as_bytes()[1] - b'0') as usize)
            )
        };
    }
    match tag {
        "em" | "i" => wrap_inline(body, "*"),
        "strong" | "b" => wrap_inline(body, "**"),
        "s" | "del" | "strike" => wrap_inline(body, "~~"),
        "code" | "kbd" | "samp" => inline_code(tree, id),
        "pre" => fenced_code(tree, id),
        "a" => {
            if let Some(href) =
                urls::safe(n.attr("href"), base).filter(|s| !s.is_empty() && !trimmed.is_empty())
            {
                format!("[{trimmed}]({})", urls::destination(&href))
            } else {
                body.into()
            }
        }
        "img" => {
            let alt = escape(normalize(n.attr("alt")).trim());
            if let Some(src) = urls::safe(n.attr("src"), base)
                .filter(|s| !s.is_empty() && !n.attr("src").is_empty())
            {
                format!("![{alt}]({})", urls::destination(&src))
            } else {
                alt
            }
        }
        "ul" | "ol" => render_list(tree, id, rendered),
        "table" => render_table(tree, id, rendered),
        "blockquote" => format!(
            "\n\n{}\n\n",
            trimmed
                .lines()
                .map(|line| if line.is_empty() {
                    ">".into()
                } else {
                    format!("> {line}")
                })
                .collect::<Vec<_>>()
                .join("\n")
        ),
        "br" => "  \n".into(),
        "hr" => "\n\n---\n\n".into(),
        "dt" => format!("\n\n{}\n", wrap_inline(trimmed, "**")),
        "dd" => format!("\n{trimmed}\n\n"),
        _ => {
            if has(BLOCKS, tag) {
                if trimmed.is_empty() {
                    String::new()
                } else {
                    format!("\n\n{trimmed}\n\n")
                }
            } else {
                body.into()
            }
        }
    }
}
pub fn render(tree: &Tree, selected: &[Id], base: Option<&str>) -> String {
    let mut output = Vec::new();
    for &root in selected {
        let mut order = Vec::new();
        let mut stack = vec![root];
        while let Some(id) = stack.pop() {
            order.push(id);
            if !has(LITERAL, &tree.nodes[id].tag) {
                stack.extend(tree.elements(id));
            }
        }
        let mut rendered: HashMap<Id, String> = HashMap::new();
        for id in order.into_iter().rev() {
            let n = &tree.nodes[id];
            let mut parts = Vec::new();
            if !has(LITERAL, &n.tag) {
                for (i, &c) in n.children.iter().enumerate() {
                    let child = &tree.nodes[c];
                    if !child.tag.is_empty() {
                        parts.push(rendered[&c].clone());
                        continue;
                    }
                    if !child.text.is_empty()
                        && child.text.trim().is_empty()
                        && (i > 0 && block_neighbor(&tree.nodes[n.children[i - 1]].tag)
                            || i + 1 < n.children.len()
                                && block_neighbor(&tree.nodes[n.children[i + 1]].tag))
                    {
                        continue;
                    }
                    parts.push(escape(&normalize(&child.text)));
                }
            }
            let body = join_parts(parts);
            let value = serialize(tree, id, &body, &rendered, base);
            rendered.insert(id, value);
        }
        output.push(rendered.remove(&root).expect("root was rendered"));
    }
    let result = join_parts(output).trim().to_owned();
    if result.is_empty() {
        result
    } else {
        format!("{result}\n")
    }
}
