use crate::{
    entities::decode,
    tree::{Id, Node, Tree, has},
};
use std::collections::HashMap;
const VOID: &str = "area base br col embed hr img input link meta param source track wbr";
const RAW: &str = "script style xmp iframe noembed noframes";
const RCDATA: &str = "title textarea";
const BREAKERS: &str = "address article aside blockquote div dl fieldset footer form h1 h2 h3 h4 h5 h6 header hr main nav ol p pre section table ul";
fn space(c: u8) -> bool {
    b"\t\n\r\x0c ".contains(&c)
}
struct Parser {
    tree: Tree,
    stack: Vec<Id>,
    recoveries: usize,
}
impl Parser {
    fn top(&self) -> Id {
        *self
            .stack
            .last()
            .expect("document root remains on the stack")
    }
    fn close_scope(&mut self, targets: &str, boundaries: &str) {
        for i in (1..self.stack.len()).rev() {
            let tag = &self.tree.nodes[self.stack[i]].tag;
            if has(targets, tag) {
                self.stack.truncate(i);
                self.recoveries += 1;
                return;
            }
            if has(boundaries, tag) {
                return;
            }
        }
    }
    fn end(&mut self, tag: &str) {
        if has(VOID, tag) {
            return;
        }
        let boundaries = match tag {
            "li" => "ul ol",
            "td" | "th" => "tr table",
            "tr" => "table",
            _ => "",
        };
        for i in (1..self.stack.len()).rev() {
            let current = &self.tree.nodes[self.stack[i]].tag;
            if current == tag {
                self.stack.truncate(i);
                return;
            }
            if has(boundaries, current) {
                break;
            }
        }
        self.recoveries += 1;
    }
    fn start(&mut self, tag: String, attrs: HashMap<String, String>, self_closing: bool) {
        if has(BREAKERS, &tag) {
            self.close_scope("p", "table td th li");
        }
        match tag.as_str() {
            "li" => self.close_scope("li", "ul ol"),
            "dt" | "dd" => self.close_scope("dt dd", "dl"),
            "tr" => self.close_scope("tr", "table tbody thead tfoot"),
            "td" | "th" => self.close_scope("td th", "tr table"),
            "thead" | "tbody" | "tfoot" => self.close_scope("thead tbody tfoot", "table"),
            "option" => self.close_scope("option", "select datalist"),
            "a" => self.close_scope("a", "p div li"),
            _ => {}
        }
        let is_void = has(VOID, &tag);
        let id = self.tree.add(
            self.top(),
            Node {
                tag: tag.clone(),
                attrs,
                ..Node::default()
            },
        );
        if !is_void {
            self.stack.push(id);
            if self_closing {
                self.end(&tag);
            }
        }
    }
    fn data(&mut self, text: &str, raw: bool) {
        if !text.is_empty() {
            self.tree.add(
                self.top(),
                Node {
                    text: if raw {
                        text.to_owned()
                    } else {
                        decode(text, false)
                    },
                    ..Node::default()
                },
            );
        }
    }
    fn feed(&mut self, html: &str) {
        let bytes = html.as_bytes();
        let mut pos = 0;
        while pos < html.len() {
            let tag = self.tree.nodes[self.top()].tag.clone();
            let rest = &html[pos..];
            if tag == "plaintext" {
                self.data(rest, true);
                break;
            }
            if has(RAW, &tag) || has(RCDATA, &tag) {
                let prefix = format!("</{tag}");
                let lower = rest.to_ascii_lowercase();
                let mut close = None;
                for (i, _) in lower.match_indices(&prefix) {
                    let mut j = i + prefix.len();
                    while j < rest.len() && space(rest.as_bytes()[j]) {
                        j += 1;
                    }
                    if rest.as_bytes().get(j) == Some(&b'>') {
                        close = Some((i, j + 1));
                        break;
                    }
                }
                if let Some((start, end)) = close {
                    self.data(&rest[..start], has(RAW, &tag));
                    self.end(&tag);
                    pos += end;
                    continue;
                }
                self.data(rest, has(RAW, &tag));
                break;
            }
            if bytes[pos] != b'<' {
                let end = rest.find('<').unwrap_or(rest.len());
                self.data(&rest[..end], false);
                pos += end;
                continue;
            }
            if rest.starts_with("<!--") {
                if rest.starts_with("<!-->") {
                    pos += 5;
                    continue;
                }
                if rest.starts_with("<!--->") {
                    pos += 6;
                    continue;
                }
                let mut end = None;
                for (i, _) in rest.match_indices("--") {
                    if i < 4 {
                        continue;
                    }
                    let mut j = i + 2;
                    while j < rest.len() && space(rest.as_bytes()[j]) {
                        j += 1;
                    }
                    if rest.as_bytes().get(j) == Some(&b'>') {
                        end = Some(j + 1);
                        break;
                    }
                    if rest[j..].starts_with("!>") {
                        end = Some(j + 2);
                        break;
                    }
                }
                if let Some(end) = end {
                    pos += end;
                    continue;
                }
                break;
            }
            if let Some(declaration) = rest.strip_prefix("<![") {
                let name: String = declaration
                    .chars()
                    .take_while(char::is_ascii_alphabetic)
                    .collect();
                if !has(
                    "temp cdata ignore include rcdata if else endif",
                    &name.to_ascii_lowercase(),
                ) {
                    self.recoveries += 1;
                    break;
                }
                if let Some(end) = rest.find('>') {
                    self.recoveries += 1;
                    pos += end + 1;
                    continue;
                }
                break;
            }
            if rest.starts_with("<!") || rest.starts_with("<?") {
                if let Some(end) = rest.find('>') {
                    pos += end + 1;
                    continue;
                }
                break;
            }
            if rest.starts_with("</") {
                let Some(end) = rest.find('>') else {
                    break;
                };
                let body = rest[2..end].trim_start();
                let name: String = body
                    .chars()
                    .take_while(|c| !c.is_whitespace() && *c != '/' && *c != '>')
                    .collect();
                if name.as_bytes().first().is_some_and(u8::is_ascii_alphabetic) {
                    self.end(&name.to_lowercase());
                }
                pos += end + 1;
                continue;
            }
            if !bytes.get(pos + 1).is_some_and(u8::is_ascii_alphabetic) {
                self.data("<", false);
                pos += 1;
                continue;
            }
            let mut cursor = 1;
            while cursor < rest.len()
                && !space(rest.as_bytes()[cursor])
                && !b"/>\0".contains(&rest.as_bytes()[cursor])
            {
                cursor += 1;
            }
            let name = rest[1..cursor].to_lowercase();
            let mut attrs = HashMap::new();
            let mut complete = false;
            let mut self_closing = false;
            while cursor < rest.len() {
                while cursor < rest.len()
                    && (space(rest.as_bytes()[cursor]) || rest.as_bytes()[cursor] == b'/')
                {
                    cursor += 1;
                }
                if rest.as_bytes().get(cursor) == Some(&b'>') {
                    self_closing = rest.as_bytes()[cursor - 1] == b'/';
                    cursor += 1;
                    complete = true;
                    break;
                }
                let start = cursor;
                while cursor < rest.len()
                    && !space(rest.as_bytes()[cursor])
                    && !b"/>=".contains(&rest.as_bytes()[cursor])
                {
                    cursor += 1;
                }
                if cursor == start {
                    break;
                }
                let attr = rest[start..cursor].to_lowercase();
                while cursor < rest.len() && space(rest.as_bytes()[cursor]) {
                    cursor += 1;
                }
                let mut value = "";
                if rest.as_bytes().get(cursor) == Some(&b'=') {
                    while rest.as_bytes().get(cursor) == Some(&b'=') {
                        cursor += 1;
                    }
                    while cursor < rest.len() && space(rest.as_bytes()[cursor]) {
                        cursor += 1;
                    }
                    if cursor >= rest.len() {
                        break;
                    }
                    let quote = rest.as_bytes()[cursor];
                    if quote == b'\'' || quote == b'"' {
                        cursor += 1;
                        let start = cursor;
                        while cursor < rest.len() && rest.as_bytes()[cursor] != quote {
                            cursor += 1;
                        }
                        if cursor == rest.len() {
                            break;
                        }
                        value = &rest[start..cursor];
                        cursor += 1;
                    } else {
                        let start = cursor;
                        while cursor < rest.len()
                            && !space(rest.as_bytes()[cursor])
                            && rest.as_bytes()[cursor] != b'>'
                        {
                            cursor += 1;
                        }
                        value = &rest[start..cursor];
                    }
                }
                attrs.insert(attr, decode(value, true));
            }
            if !complete {
                break;
            }
            self.start(name, attrs, self_closing);
            pos += cursor;
        }
    }
}
pub fn parse(html: &str) -> (Tree, Vec<String>) {
    let mut parser = Parser {
        tree: Tree::new(),
        stack: vec![0],
        recoveries: 0,
    };
    parser.feed(html);
    let notes = if parser.recoveries > 0 {
        vec!["Recovered malformed or optionally closed HTML.".into()]
    } else {
        vec![]
    };
    (parser.tree, notes)
}
