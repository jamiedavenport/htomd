use std::collections::HashMap;
pub type Id = usize;
#[derive(Default)]
pub struct Node {
    pub tag: String,
    pub attrs: HashMap<String, String>,
    pub children: Vec<Id>,
    pub parent: Option<Id>,
    pub text: String,
}
impl Node {
    pub fn attr(&self, key: &str) -> &str {
        self.attrs.get(key).map(String::as_str).unwrap_or("")
    }
}
// Parent and child edges are IDs. Traversal and destruction never recurse through ownership.
pub struct Tree {
    pub nodes: Vec<Node>,
}
impl Tree {
    pub fn new() -> Self {
        Self {
            nodes: vec![Node {
                tag: "#document".into(),
                ..Node::default()
            }],
        }
    }
    pub fn add(&mut self, parent: Id, mut node: Node) -> Id {
        let id = self.nodes.len();
        node.parent = Some(parent);
        self.nodes.push(node);
        self.nodes[parent].children.push(id);
        id
    }
    pub fn walk(&self, root: Id) -> Vec<Id> {
        let mut result = Vec::new();
        let mut stack = vec![root];
        while let Some(id) = stack.pop() {
            if self.nodes[id].tag.is_empty() {
                continue;
            }
            result.push(id);
            stack.extend(self.nodes[id].children.iter().rev().copied());
        }
        result
    }
    pub fn elements(&self, id: Id) -> Vec<Id> {
        self.nodes[id]
            .children
            .iter()
            .copied()
            .filter(|&c| !self.nodes[c].tag.is_empty())
            .collect()
    }
    pub fn text(&self, id: Id, normalized: bool) -> String {
        let mut value = String::new();
        let mut stack = vec![id];
        while let Some(id) = stack.pop() {
            let n = &self.nodes[id];
            if n.tag.is_empty() {
                value.push_str(&n.text);
            } else {
                stack.extend(n.children.iter().rev().copied());
            }
        }
        if normalized {
            normalize(&value).trim().to_owned()
        } else {
            value
        }
    }
}
pub fn has(words: &str, word: &str) -> bool {
    words.split_ascii_whitespace().any(|w| w == word)
}
pub fn normalize(s: &str) -> String {
    let mut out = String::new();
    let mut space = false;
    for c in s.chars() {
        if c.is_whitespace() {
            if !space {
                out.push(' ');
            }
            space = true;
        } else {
            out.push(c);
            space = false;
        }
    }
    out
}
