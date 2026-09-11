import { decodeEntities } from "./entities.js";
import { Node } from "./tree.js";

const VOID = new Set(
  "area base br col embed hr img input link meta param source track wbr".split(" "),
);
const RAW_TEXT = new Set(["script", "style", "xmp", "iframe", "noembed", "noframes"]);
const RCDATA = new Set(["title", "textarea"]);
const P_BREAKERS = new Set(
  "address article aside blockquote div dl fieldset footer form h1 h2 h3 h4 h5 h6 header hr main nav ol p pre section table ul".split(
    " ",
  ),
);
const IMPLIED = new Map<string, [readonly string[], readonly string[]]>([
  ["li", [["li"], ["ul", "ol"]]],
  ["dt", [["dt", "dd"], ["dl"]]],
  ["dd", [["dt", "dd"], ["dl"]]],
  ["tr", [["tr"], ["table", "tbody", "thead", "tfoot"]]],
  [
    "td",
    [
      ["td", "th"],
      ["tr", "table"],
    ],
  ],
  [
    "th",
    [
      ["td", "th"],
      ["tr", "table"],
    ],
  ],
  ["thead", [["thead", "tbody", "tfoot"], ["table"]]],
  ["tbody", [["thead", "tbody", "tfoot"], ["table"]]],
  ["tfoot", [["thead", "tbody", "tfoot"], ["table"]]],
  ["option", [["option"], ["select", "datalist"]]],
]);
const END_SCOPES = new Map<string, readonly string[]>([
  ["li", ["ul", "ol"]],
  ["td", ["tr", "table"]],
  ["th", ["tr", "table"]],
  ["tr", ["table"]],
]);

class TreeParser {
  readonly root = new Node("#document");
  // The document stays at index zero; scope closure never removes it.
  private readonly stack = [this.root];
  recoveries = 0;

  private closeInScope(targets: readonly string[], boundaries: readonly string[]): void {
    for (let index = this.stack.length - 1; index > 0; index--) {
      const tag = this.stack[index]!.tag;
      if (targets.includes(tag)) {
        this.stack.length = index;
        this.recoveries++;
        return;
      }
      if (boundaries.includes(tag)) {
        return;
      }
    }
  }

  private start(tag: string, attrs: Map<string, string>, selfClosing: boolean): void {
    if (P_BREAKERS.has(tag)) {
      this.closeInScope(["p"], ["table", "td", "th", "li"]);
    }
    const implied = IMPLIED.get(tag);
    if (implied) {
      this.closeInScope(...implied);
    }
    if (tag === "a") {
      this.closeInScope(["a"], ["p", "div", "li"]);
    }
    const parent = this.stack[this.stack.length - 1]!;
    const node = new Node(tag, attrs, parent);
    parent.children.push(node);
    if (!VOID.has(tag)) {
      this.stack.push(node);
      if (selfClosing) {
        this.end(tag);
      }
    }
  }

  private end(tag: string): void {
    if (VOID.has(tag)) {
      return;
    }
    for (let index = this.stack.length - 1; index > 0; index--) {
      const current = this.stack[index]!.tag;
      if (current === tag) {
        this.stack.length = index;
        return;
      }
      if (END_SCOPES.get(tag)?.includes(current)) {
        break;
      }
    }
    this.recoveries++;
  }

  private data(value: string, raw = false): void {
    if (value) {
      this.stack[this.stack.length - 1]!.children.push(raw ? value : decodeEntities(value));
    }
  }

  feed(html: string): void {
    let position = 0;
    while (position < html.length) {
      const parent = this.stack[this.stack.length - 1]!;
      if (parent.tag === "plaintext") {
        this.data(html.slice(position), true);
        break;
      }
      if (RAW_TEXT.has(parent.tag) || RCDATA.has(parent.tag)) {
        const close = new RegExp(`</${parent.tag}[\\t\\n\\r\\f ]*>`, "gi");
        close.lastIndex = position;
        const match = close.exec(html);
        if (!match) {
          this.data(html.slice(position), RAW_TEXT.has(parent.tag));
          break;
        }
        this.data(html.slice(position, match.index), RAW_TEXT.has(parent.tag));
        this.end(parent.tag);
        position = close.lastIndex;
        continue;
      }
      if (html[position] !== "<") {
        const next = html.indexOf("<", position);
        const end = next < 0 ? html.length : next;
        this.data(html.slice(position, end));
        position = end;
        continue;
      }
      const rest = html.slice(position);
      if (rest.startsWith("<!--")) {
        const closing = /^(?:<!-->|<!--->)|--\s*>|--!>/g;
        const match = closing.exec(rest);
        if (!match) {
          break;
        }
        position += match.index + match[0].length;
        continue;
      }
      if (rest.startsWith("<![")) {
        const match = /^<!\[([a-z]+)\b/i.exec(rest);
        if (
          !match ||
          !["temp", "cdata", "ignore", "include", "rcdata", "if", "else", "endif"].includes(
            match[1]!.toLowerCase(),
          )
        ) {
          this.recoveries++;
          break;
        }
        const close = /]\s*]\s*>|]\s*>/.exec(rest);
        if (!close) {
          break;
        }
        this.recoveries++;
        position += close.index + close[0].length;
        continue;
      }
      if (/^<!|^<\?/.test(rest)) {
        const end = rest.indexOf(">");
        if (end < 0) {
          break;
        }
        position += end + 1;
        continue;
      }
      if (rest.startsWith("</")) {
        const end = rest.indexOf(">");
        if (end < 0) {
          break;
        }
        const match = /^<\/\s*([a-z][^\s/>]*)/i.exec(rest);
        if (match) {
          this.end(match[1]!.toLowerCase());
        }
        position += end + 1;
        continue;
      }
      // NUL cannot form part of a tag name.
      // oxlint-disable-next-line no-control-regex
      const name = /^<([a-z][^\t\n\r\f />\x00]*)/i.exec(rest);
      if (!name) {
        this.data("<");
        position++;
        continue;
      }
      const attrs = new Map<string, string>();
      let cursor = name[0].length;
      let complete = false;
      let selfClosing = false;
      while (cursor < rest.length) {
        const gap = /^[\t\n\r\f /]+/.exec(rest.slice(cursor));
        if (gap) {
          cursor += gap[0].length;
        }
        if (rest[cursor] === ">") {
          selfClosing = rest[cursor - 1] === "/";
          cursor++;
          complete = true;
          break;
        }
        const attr =
          /^([^\t\n\r\f />=]+)(?:[\t\n\r\f ]*=+[\t\n\r\f ]*(?:"([^"]*)"|'([^']*)'|([^\t\n\r\f >]*)))?/.exec(
            rest.slice(cursor),
          );
        if (!attr || attr[4]?.startsWith('"') || attr[4]?.startsWith("'")) {
          break;
        }
        attrs.set(
          attr[1]!.toLowerCase(),
          decodeEntities(attr[2] ?? attr[3] ?? attr[4] ?? "", true),
        );
        cursor += attr[0].length;
      }
      if (!complete) {
        break;
      }
      this.start(name[1]!.toLowerCase(), attrs, selfClosing);
      position += cursor;
    }
  }
}

export function parse(html: string): [Node, string[]] {
  const parser = new TreeParser();
  parser.feed(html);
  return [parser.root, parser.recoveries ? ["Recovered malformed or optionally closed HTML."] : []];
}
