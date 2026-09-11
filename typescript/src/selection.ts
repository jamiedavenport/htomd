import type { Diagnostics } from "./models.js";
import { Node, elements, postorder, walk } from "./tree.js";

const INERT = new Set(
  "head title meta link base script style template noscript iframe object embed svg canvas nav button input select textarea dialog".split(
    " ",
  ),
);
const NAV_ROLES = new Set("navigation banner contentinfo menu menubar dialog".split(" "));
const STRUCTURES = new Set("ul ol dl table blockquote pre".split(" "));
const CONTAINERS = new Set("article main section div body #document".split(" "));
const EVIDENCE = new Set("p pre li dt dd td th blockquote".split(" "));
export const HEADINGS = new Set("h1 h2 h3 h4 h5 h6".split(" "));
const NEGATIVE = new Set(
  "advertisement ads advert promo promotion related share sharing social cookie consent newsletter comments comment sidebar breadcrumb breadcrumbs pagination toolbar footer banner dropdown catlinks menu pager teaser toc well".split(
    " ",
  ),
);
const POSITIVE = new Set("article content main post entry story text documentation".split(" "));
const REFERENCES = new Set("footnotes references endnotes bibliography".split(" "));
const HIDDEN_STYLE =
  /(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))\s*(?:!important\s*)?(?:;|$)/i;
const STAT_FIELDS = [
  "characters",
  "linked",
  "punctuation",
  "blocks",
  "headings",
  "code",
  "cells",
  "images",
  "controls",
] as const;

export class Stats {
  characters = 0;
  linked = 0;
  punctuation = 0;
  blocks = 0;
  headings = 0;
  code = 0;
  cells = 0;
  images = 0;
  controls = 0;
  get density(): number {
    return this.linked / Math.max(1, this.characters);
  }
}

function hints(node: Node): Set<string> {
  const value = `${node.attrs.get("class") ?? ""} ${node.attrs.get("id") ?? ""}`;
  return new Set(
    value
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .toLowerCase()
      .match(/[a-z0-9]+/g) ?? [],
  );
}

function intersects(left: ReadonlySet<string>, right: ReadonlySet<string>): boolean {
  for (const value of left) {
    if (right.has(value)) {
      return true;
    }
  }
  return false;
}

function excluded(node: Node, local: boolean): boolean {
  if (
    INERT.has(node.tag) ||
    node.attrs.has("hidden") ||
    node.attrs.get("aria-hidden")?.toLowerCase() === "true" ||
    HIDDEN_STYLE.test(node.attrs.get("style") ?? "")
  ) {
    return true;
  }
  if (node.tag === "a" && hints(node).has("headerlink")) {
    return (node.attrs.get("href") ?? "").startsWith("#");
  }
  if (NAV_ROLES.has((node.attrs.get("role") ?? "").toLowerCase())) {
    return true;
  }
  return (node.tag === "header" || node.tag === "footer") && !local;
}

export function visibleTree(root: Node): Node {
  const stack: [Node, boolean][] = [[root, false]];
  while (stack.length) {
    const [node, inherited] = stack.pop()!;
    const local =
      inherited ||
      node.tag === "article" ||
      node.tag === "main" ||
      node.attrs.get("role") === "main";
    node.children = node.children.filter((child) => {
      if (child instanceof Node) {
        if (excluded(child, local)) {
          return false;
        }
        stack.push([child, local]);
      }
      return true;
    });
  }
  return root;
}

export function statistics(root: Node, result = new Map<Node, Stats>()): Map<Node, Stats> {
  // Postorder populates every child before its parent. Cleanup invalidates only
  // changed ancestors; all surviving nodes retain entries for selection.
  for (const node of postorder(root)) {
    if (result.has(node)) {
      continue;
    }
    const stat = new Stats();
    for (const child of node.children) {
      if (typeof child === "string") {
        stat.characters += Array.from(child.trim()).length;
        stat.punctuation += (child.match(/[,.;:!?。，；：！？،؛]/gu) ?? []).length;
      } else {
        const other = result.get(child)!;
        for (const key of STAT_FIELDS) {
          stat[key] += other[key];
        }
      }
    }
    stat.blocks += Number(EVIDENCE.has(node.tag) && stat.characters > 0);
    stat.headings += Number(HEADINGS.has(node.tag) && stat.characters > 0);
    stat.code += Number(node.tag === "pre");
    stat.cells += Number(node.tag === "td" || node.tag === "th");
    stat.images += Number(node.tag === "img" && Boolean(node.attrs.get("src")));
    stat.controls += Number(["form", "button", "input", "select", "textarea"].includes(node.tag));
    if (node.tag === "a") {
      stat.linked = stat.characters;
    }
    result.set(node, stat);
  }
  return result;
}

function conditionalClutter(node: Node, stat: Stats): boolean {
  if (["#document", "html", "body", "main", "article"].includes(node.tag)) {
    return false;
  }
  const tokens = hints(node);
  if (intersects(tokens, REFERENCES) || node.attrs.get("role") === "note") {
    return false;
  }
  if (!intersects(tokens, NEGATIVE) || EVIDENCE.has(node.tag) || HEADINGS.has(node.tag)) {
    return false;
  }
  if (stat.density > 0.35 || stat.controls) {
    return true;
  }
  if (tokens.has("footer") && stat.density > 0.15) {
    return true;
  }
  if (node.tag === "aside" && !stat.code && !stat.cells) {
    return true;
  }
  if (!stat.blocks && stat.characters < 180) {
    return true;
  }
  if (tokens.has("comments") || tokens.has("comment")) {
    return (
      elements(node).filter((child) => {
        const childHints = hints(child);
        return childHints.has("comment") || childHints.has("reply");
      }).length >= 2
    );
  }
  return false;
}

export function clean(root: Node): [Map<Node, Stats>, number] {
  const stats = statistics(root);
  const changed = new Set<Node>();
  let removed = 0;
  for (const node of walk(root)) {
    node.children = node.children.filter((child) => {
      if (child instanceof Node && conditionalClutter(child, stats.get(child)!)) {
        removed++;
        changed.add(node);
        return false;
      }
      return true;
    });
  }
  for (const node of changed) {
    let ancestor: Node | null = node;
    while (ancestor && stats.has(ancestor)) {
      stats.delete(ancestor);
      ancestor = ancestor.parent;
    }
  }
  return [removed ? statistics(root, stats) : stats, removed];
}

function plausible(node: Node, stat: Stats, semantic = false): boolean {
  if (!stat.characters) {
    return semantic && Boolean(stat.images);
  }
  if (stat.code || stat.cells) {
    return true;
  }
  if (node.tag === "p" && stat.characters > stat.linked) {
    return true;
  }
  if (stat.density >= 0.8) {
    return semantic && Boolean(stat.headings && stat.blocks);
  }
  return (
    CONTAINERS.has(node.tag) ||
    EVIDENCE.has(node.tag) ||
    HEADINGS.has(node.tag) ||
    STRUCTURES.has(node.tag) ||
    semantic
  );
}

function scores(root: Node, stats: Map<Node, Stats>, relaxed: boolean): Map<Node, number> {
  const result = new Map<Node, number>();
  for (const node of walk(root)) {
    const stat = stats.get(node)!;
    if (!CONTAINERS.has(node.tag) || !plausible(node, stat)) {
      continue;
    }
    const tokens = hints(node);
    let score = Math.sqrt(stat.characters) + Math.min(stat.blocks, 30) * 2;
    score += Math.min(stat.punctuation, 40) * 0.25 + Math.min(stat.code + stat.cells, 12) * 2;
    score += 8 * Number(intersects(tokens, POSITIVE));
    if (!relaxed) {
      score -= 18 * Number(intersects(tokens, NEGATIVE));
    }
    result.set(node, score * (1 - stat.density) ** 2);
  }
  for (const node of walk(root)) {
    if (!EVIDENCE.has(node.tag) || elements(node).some((child) => EVIDENCE.has(child.tag))) {
      continue;
    }
    const stat = stats.get(node)!;
    const support = (1 + Math.min(stat.characters / 100, 3)) * (1 - stat.density);
    let ancestor = node.parent;
    for (const weight of [1, 0.5, 0.25]) {
      if (!ancestor) {
        break;
      }
      const score = result.get(ancestor);
      if (score !== undefined) {
        result.set(ancestor, score + support * weight);
      }
      ancestor = ancestor.parent;
    }
  }
  return result;
}

function highest(nodes: Iterable<Node>, ranked: Map<Node, number>): Node | null {
  let winner: Node | null = null;
  let best = -Infinity;
  for (const node of nodes) {
    const score = ranked.get(node) ?? 0;
    if (score > best) {
      winner = node;
      best = score;
    }
  }
  return winner;
}

function semanticCandidate(
  root: Node,
  stats: Map<Node, Stats>,
  ranked: Map<Node, number>,
): Node | null {
  const candidates: Node[] = [];
  const landmarks: Node[] = [];
  for (const node of walk(root)) {
    const landmark = node.tag === "main" || node.attrs.get("role") === "main";
    if (!landmark && node.tag !== "article") {
      continue;
    }
    const stat = stats.get(node)!;
    if (
      !plausible(node, stat, true) ||
      conditionalClutter(node, stat) ||
      (hints(node).has("teaser") && stat.density > 0.1)
    ) {
      continue;
    }
    candidates.push(node);
    if (landmark) {
      landmarks.push(node);
    }
  }
  return highest(landmarks.length ? landmarks : candidates, ranked);
}

function recoverSiblings(winner: Node, stats: Map<Node, Stats>, ranked: Map<Node, number>): Node[] {
  if (!winner.parent) {
    return [winner];
  }
  const threshold = Math.max(5, (ranked.get(winner) ?? 0) * 0.18);
  return elements(winner.parent).filter((sibling) => {
    const stat = stats.get(sibling)!;
    if (conditionalClutter(sibling, stat)) {
      return false;
    }
    const supported = (ranked.get(sibling) ?? 0) >= threshold && stat.density < 0.5;
    const heading = HEADINGS.has(sibling.tag) && stat.density < 0.5;
    const paragraph = sibling.tag === "p" && stat.density < 0.25 && stat.characters > 0;
    return sibling === winner || supported || heading || paragraph;
  });
}

function fallback(root: Node, stats: Map<Node, Stats>): Node[] {
  const selected: Node[] = [];
  const stack = [root];
  while (stack.length && selected.length < 256) {
    const node = stack.pop()!;
    const stat = stats.get(node)!;
    if (conditionalClutter(node, stat)) {
      continue;
    }
    const children = elements(node);
    if (
      ((EVIDENCE.has(node.tag) || HEADINGS.has(node.tag) || STRUCTURES.has(node.tag)) &&
        plausible(node, stat)) ||
      (!children.length && stat.characters > 0 && stat.density < 0.5)
    ) {
      selected.push(node);
    } else {
      for (let index = children.length - 1; index >= 0; index--) {
        stack.push(children[index]!);
      }
    }
  }
  return selected;
}

export function select(root: Node): [Node[], Diagnostics] {
  const visible = visibleTree(root);
  const [stats, removed] = clean(visible);
  let ranked = scores(visible, stats, false);
  const notes = removed ? [`Removed ${removed} conditionally identified clutter blocks.`] : [];
  let winner = semanticCandidate(visible, stats, ranked);
  if (winner) {
    return [[winner], { strategy: "semantic", notes }];
  }
  const candidates = () =>
    [...ranked.keys()].filter((node) => node.tag !== "body" && node.tag !== "#document");
  winner = highest(candidates(), ranked);
  if (!winner || (ranked.get(winner) ?? 0) < 5) {
    notes.push("Retried selection once with relaxed class penalties.");
    ranked = scores(visible, stats, true);
    winner = highest(candidates(), ranked);
  }
  if (winner && (ranked.get(winner) ?? 0) >= 5) {
    return [recoverSiblings(winner, stats, ranked), { strategy: "scored", notes }];
  }
  const recovered = fallback(visible, stats);
  notes.push(
    recovered.length ? "Recovered plausible blocks." : "No relevant visible content found.",
  );
  return [recovered, { strategy: recovered.length ? "fallback" : "none", notes }];
}
