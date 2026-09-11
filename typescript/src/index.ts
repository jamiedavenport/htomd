import { readMetadata, refineMetadata } from "./metadata.js";
import type { Document, ExtractOptions } from "./models.js";
import { parse } from "./parser.js";
import { render } from "./render.js";
import { select } from "./selection.js";
import { documentBase } from "./urls.js";

export type { Diagnostics, Document, ExtractOptions, Metadata } from "./models.js";

/** Extract Markdown and metadata from decoded HTML, without fetching anything. */
export function extract(html: string, options: ExtractOptions = {}): Document {
  if (typeof html !== "string") {
    throw new TypeError("html must be a decoded string");
  }
  const url = options.url ?? null;
  if (url !== null && typeof url !== "string") {
    throw new TypeError("url must be a string or null");
  }
  const [root, parsingNotes] = parse(html);
  const base = documentBase(root, url);
  const metadata = readMetadata(root, url, base);
  const [selected, diagnostics] = select(root);
  const refined = refineMetadata(metadata, selected);
  const markdown = render(selected, base);
  return Object.freeze({
    markdown,
    metadata: Object.freeze(refined),
    diagnostics: Object.freeze({
      strategy: markdown ? diagnostics.strategy : "none",
      notes: Object.freeze([...parsingNotes, ...diagnostics.notes]),
    }),
  });
}

/** Return only the Markdown produced by extract. */
export function convert(html: string, options: ExtractOptions = {}): string {
  return extract(html, options).markdown;
}
