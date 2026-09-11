import { HEADINGS } from "./selection.js";
import { Node, SPACE, elements, postorder, textContent } from "./tree.js";
import { destination, safeUrl } from "./urls.js";

const EMPHASIS = new Map([
  ["em", "*"],
  ["i", "*"],
  ["strong", "**"],
  ["b", "**"],
  ["s", "~~"],
  ["del", "~~"],
  ["strike", "~~"],
]);
const LITERAL_TAGS = new Set(["pre", "code", "kbd", "samp"]);
const BLOCKS = new Set(
  "p div article main section header footer figure figcaption address details summary dl".split(
    " ",
  ),
);
const BLOCK_NEIGHBORS = new Set([
  ...BLOCKS,
  ...HEADINGS,
  "ul",
  "ol",
  "pre",
  "table",
  "blockquote",
  "hr",
  "li",
]);

function escape(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replace(/([\\`*_~[\]])/g, "\\$1")
    .replace(
      /(^|\n)(\s*)(#{1,6}(?=\s)|[-+](?=\s)|\d+[.)](?=\s)|[=~-]{3,}(?=\s|$))/g,
      (_match: string, prefix: string, space: string, marker: string) =>
        prefix +
        space +
        (/^\d/.test(marker) ? `${marker.slice(0, -1)}\\${marker.slice(-1)}` : `\\${marker}`),
    );
}

function longestBackticks(value: string): number {
  let longest = 0;
  for (const match of value.matchAll(/`+/g)) {
    longest = Math.max(longest, match[0].length);
  }
  return longest;
}

function inlineCode(node: Node): string {
  const value = textContent(node, false).replace(/\r\n|\r|\n/g, " ");
  if (!value) {
    return "";
  }
  const delimiter = "`".repeat(longestBackticks(value) + 1);
  const padding =
    value.startsWith("`") ||
    value.endsWith("`") ||
    (value.startsWith(" ") && value.endsWith(" ") && value.trim())
      ? " "
      : "";
  return delimiter + padding + value + padding + delimiter;
}

function codeLanguage(node: Node): string {
  const candidates = [node, ...elements(node)];
  if (node.parent) {
    candidates.push(node.parent);
  }
  const valid = /^[\p{L}\p{N}_.+#-]+$/u;
  for (const candidate of candidates) {
    for (const token of (candidate.attrs.get("class") ?? "").split(SPACE)) {
      if (/^(?:language|lang|highlight)-/.test(token)) {
        const value = token.slice(token.indexOf("-") + 1);
        if (valid.test(value)) {
          return value;
        }
      }
    }
    const value = candidate.attrs.get("data-language") ?? "";
    if (valid.test(value)) {
      return value;
    }
  }
  return "";
}

function fencedCode(node: Node): string {
  const value = textContent(node, false).replace(/\r\n|\r/g, "\n");
  const fence = "`".repeat(Math.max(3, longestBackticks(value) + 1));
  return `\n\n${fence}${codeLanguage(node)}\n${value}${value.endsWith("\n") ? "" : "\n"}${fence}\n\n`;
}

function joinParts(parts: string[]): string {
  const result: string[] = [];
  for (let part of parts) {
    if (!part) {
      continue;
    }
    const previous = result.at(-1);
    if (previous?.endsWith("\n") && part.startsWith("\n")) {
      result[result.length - 1] = previous.replace(/\n+$/, "");
      part = "\n\n" + part.replace(/^\n+/, "");
    }
    result.push(part);
  }
  return result.join("");
}

function wrapInline(body: string, marker: string): string {
  const content = body.trim();
  if (!content) {
    return body;
  }
  const leading = /^\s/u.test(body) ? " " : "";
  const trailing = /\s$/u.test(body) ? " " : "";
  return leading + marker + content + marker + trailing;
}

function renderLink(node: Node, body: string, base: string | null): string {
  const href = safeUrl(node.attrs.get("href") ?? "", base);
  return href && body.trim() ? `[${body.trim()}](${destination(href)})` : body;
}

function renderImage(node: Node, base: string | null): string {
  const alt = escape((node.attrs.get("alt") ?? "").replace(SPACE, " ").trim());
  const source = safeUrl(node.attrs.get("src") ?? "", base);
  return source && node.attrs.get("src") ? `![${alt}](${destination(source)})` : alt;
}

function lines(value: string): string[] {
  if (!value) {
    return [];
  }
  // Preserve the reference's line boundaries within list and quote content.
  // oxlint-disable-next-line no-control-regex
  return value.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/u);
}

function renderList(node: Node, rendered: Map<Node, string>): string {
  const start = (node.attrs.get("start") ?? "1").trim();
  let number = /^[+-]?\d+$/.test(start) ? BigInt(start) : 1n;
  const items: string[] = [];
  for (const child of elements(node)) {
    if (child.tag !== "li") {
      continue;
    }
    if (node.tag === "ol") {
      const value = child.attrs.get("value") ?? "";
      if (/^-?\d{1,9}$/.test(value)) {
        number = BigInt(value);
      }
    }
    const marker = node.tag === "ol" ? `${number}. ` : "- ";
    const [first, ...rest] = lines(rendered.get(child)!.trim());
    if (first !== undefined) {
      const continuation = rest.map((line) => (line ? " ".repeat(marker.length) + line : ""));
      items.push([marker + first, ...continuation].join("\n"));
    }
    number++;
  }
  return items.length ? "\n" + items.join("\n") + "\n" : "";
}

function tableRows(node: Node): Node[] {
  const rows: Node[] = [];
  const stack = elements(node).reverse();
  while (stack.length) {
    const child = stack.pop()!;
    if (child.tag === "tr") {
      rows.push(child);
    } else if (["thead", "tbody", "tfoot"].includes(child.tag)) {
      stack.push(...elements(child).reverse());
    }
  }
  return rows;
}

function simpleTable(rows: Node[][]): boolean {
  if (!rows[0]?.length || rows.some((row) => row.length !== rows[0]!.length)) {
    return false;
  }
  for (const row of rows) {
    for (const cell of row) {
      if (
        (cell.attrs.get("colspan") ?? "1") !== "1" ||
        (cell.attrs.get("rowspan") ?? "1") !== "1" ||
        elements(cell).some((child) => ["table", "pre", "ul", "ol", "p"].includes(child.tag))
      ) {
        return false;
      }
    }
  }
  return true;
}

function renderTable(node: Node, rendered: Map<Node, string>): string {
  const rows = tableRows(node).map((row) =>
    elements(row).filter((cell) => cell.tag === "th" || cell.tag === "td"),
  );
  const captions = elements(node)
    .filter((child) => child.tag === "caption")
    .map((child) => rendered.get(child)!.trim());
  if (!simpleTable(rows)) {
    const output = rows.map(
      (row, index) =>
        `${index + 1}. ` +
        row.map((cell) => rendered.get(cell)!.trim().replaceAll("\n", " ")).join(" — "),
    );
    return "\n\n" + [...captions, output.join("\n")].join("\n\n") + "\n\n";
  }
  // simpleTable establishes a nonempty rectangular first row.
  const first = rows[0]!;
  const values = rows.map((row) =>
    row.map((cell) => rendered.get(cell)!.trim().replaceAll("|", "\\|").replaceAll("\n", " ")),
  );
  if (!first.some((cell) => cell.tag === "th")) {
    values.unshift(first.map(() => ""));
  }
  values.splice(
    1,
    0,
    first.map(() => "---"),
  );
  return (
    "\n\n" +
    [...captions, values.map((row) => "| " + row.join(" | ") + " |").join("\n")].join("\n\n") +
    "\n\n"
  );
}

function serialize(
  node: Node,
  body: string,
  rendered: Map<Node, string>,
  base: string | null,
): string {
  const tag = node.tag;
  if (HEADINGS.has(tag)) {
    return body.trim() ? "\n\n" + "#".repeat(Number(tag[1])) + " " + body.trim() + "\n\n" : "";
  }
  const emphasis = EMPHASIS.get(tag);
  if (emphasis) {
    return wrapInline(body, emphasis);
  }
  if (["code", "kbd", "samp"].includes(tag)) {
    return inlineCode(node);
  }
  switch (tag) {
    case "pre":
      return fencedCode(node);
    case "a":
      return renderLink(node, body, base);
    case "img":
      return renderImage(node, base);
    case "ul":
    case "ol":
      return renderList(node, rendered);
    case "table":
      return renderTable(node, rendered);
    case "blockquote":
      return (
        "\n\n" +
        lines(body.trim())
          .map((line) => (line ? "> " + line : ">"))
          .join("\n") +
        "\n\n"
      );
    case "br":
      return "  \n";
    case "hr":
      return "\n\n---\n\n";
    case "dt":
      return "\n\n" + wrapInline(body.trim(), "**") + "\n";
    case "dd":
      return "\n" + body.trim() + "\n\n";
    default:
      return BLOCKS.has(tag) ? (body.trim() ? "\n\n" + body.trim() + "\n\n" : "") : body;
  }
}

function childParts(node: Node, rendered: Map<Node, string>): string[] {
  const parts: string[] = [];
  for (const [index, child] of node.children.entries()) {
    if (child instanceof Node) {
      parts.push(rendered.get(child)!);
      continue;
    }
    if (/^\p{White_Space}+$/u.test(child)) {
      const previous = node.children[index - 1];
      const following = node.children[index + 1];
      if (
        (previous instanceof Node && BLOCK_NEIGHBORS.has(previous.tag)) ||
        (following instanceof Node && BLOCK_NEIGHBORS.has(following.tag))
      ) {
        continue;
      }
    }
    parts.push(escape(child.replace(SPACE, " ")));
  }
  return parts;
}

export function render(selected: Node[], base: string | null): string {
  const output: string[] = [];
  for (const root of selected) {
    // Postorder fills the cache before a parent reads its children. Literal code
    // nodes read raw text directly and never consult descendant cache entries.
    const rendered = new Map<Node, string>();
    for (const node of postorder(root, LITERAL_TAGS)) {
      const parts = LITERAL_TAGS.has(node.tag) ? [] : childParts(node, rendered);
      rendered.set(node, serialize(node, joinParts(parts), rendered, base));
    }
    output.push(rendered.get(root)!);
  }
  const result = joinParts(output).trim();
  return result ? result + "\n" : "";
}
