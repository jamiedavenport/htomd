import { Node, walk } from "./tree.js";

const SAFE_SCHEMES = new Set(["", "http", "https", "mailto", "tel", "ftp"]);

function allowed(value: string): boolean {
  // Ignore ASCII controls when checking for disguised active schemes.
  // oxlint-disable-next-line no-control-regex
  const checked = value.replace(/[\x00-\x20\x7f]+/g, "");
  const scheme = /^([a-z][a-z\d+.-]*):/i.exec(checked)?.[1]?.toLowerCase() ?? "";
  if (!SAFE_SCHEMES.has(scheme)) {
    return false;
  }
  // Validate authorities with the native URL parser, including IDNA and IPv6.
  if (/^(?:[a-z][a-z\d+.-]*:)?\/\//i.test(checked)) {
    return URL.canParse(checked, "https://htomd.invalid/");
  }
  return true;
}

export function safeUrl(input: string, base: string | null = null): string | null {
  const value = input.trim();
  if (!allowed(value)) {
    return null;
  }
  if (!base || !URL.canParse(base)) {
    return value;
  }
  // Leave absolute references as supplied; resolve relative references natively.
  if (/^[a-z][a-z\d+.-]*:/i.test(value)) {
    return value;
  }
  const resolved = URL.parse(value, base)?.href ?? value;
  return allowed(resolved) ? resolved : null;
}

export function documentBase(root: Node, url: string | null): string | null {
  const source = url ? safeUrl(url) : null;
  for (const node of walk(root)) {
    if (node.tag !== "base" || !node.attrs.has("href")) {
      continue;
    }
    const candidate = safeUrl(node.attrs.get("href")!, source);
    if (candidate) {
      const parsed = URL.parse(candidate);
      if (parsed && (parsed.protocol === "http:" || parsed.protocol === "https:") && parsed.host) {
        return candidate;
      }
    }
  }
  return source;
}

export function destination(value: string): string {
  return value.replace(/[^a-zA-Z\d/:?#@!$&'*+,;=%[\]~_.-]/gu, (character) =>
    encodeURIComponent(character.toWellFormed()).replace(
      /[()]/g,
      (part) => `%${part.charCodeAt(0).toString(16).toUpperCase()}`,
    ),
  );
}
