import type { Metadata } from "./models.js";
import { Node, SPACE, textContent, walk } from "./tree.js";
import { safeUrl } from "./urls.js";

const ARTICLE_TYPES = new Set(
  "Article NewsArticle BlogPosting TechArticle ScholarlyArticle MedicalScholarlyArticle Report AnalysisNewsArticle OpinionNewsArticle ReviewNewsArticle BackgroundNewsArticle APIReference LiveBlogPosting".split(
    " ",
  ),
);

function string(value: unknown): string | null {
  return typeof value === "string" ? value.trim() || null : null;
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function articleFromJson(value: unknown): Record<string, unknown> | null {
  const stack = [value];
  while (stack.length) {
    const item = stack.pop();
    if (Array.isArray(item)) {
      for (let index = item.length - 1; index >= 0; index--) {
        stack.push(item[index]);
      }
    } else if (record(item)) {
      const kinds = typeof item["@type"] === "string" ? [item["@type"]] : item["@type"];
      if (
        Array.isArray(kinds) &&
        kinds.some(
          (kind: unknown) => typeof kind === "string" && ARTICLE_TYPES.has(kind.split("/").at(-1)!),
        )
      ) {
        return item;
      }
      if (record(item["@graph"]) || Array.isArray(item["@graph"])) {
        stack.push(item["@graph"]);
      }
    }
  }
  return null;
}

function authorName(value: unknown): string | null {
  const names: string[] = [];
  const stack = [value];
  while (stack.length) {
    const item = stack.pop();
    if (Array.isArray(item)) {
      for (let index = item.length - 1; index >= 0; index--) {
        stack.push(item[index]);
      }
    } else {
      const name = string(record(item) ? item.name : item);
      if (name) {
        names.push(name);
      }
    }
  }
  return names.join(", ") || null;
}

function readJsonLd(node: Node): Record<string, unknown> | null {
  if (node.attrs.get("type")?.toLowerCase() !== "application/ld+json") {
    return null;
  }
  try {
    return articleFromJson(JSON.parse(textContent(node, false)));
  } catch {
    return null;
  }
}

export function readMetadata(root: Node, url: string | null, base: string | null): Metadata {
  const fields = new Map<string, string>();
  let article: Record<string, unknown> | null = null;
  let title: string | null = null;
  let language: string | null = null;
  let canonical: string | null = null;
  for (const node of walk(root)) {
    if (node.tag === "meta") {
      const key = (node.attrs.get("property") ?? node.attrs.get("name") ?? "").toLowerCase();
      const content = string(node.attrs.get("content"));
      if (content && !fields.has(key)) {
        fields.set(key, content);
      }
    } else if (node.tag === "title" && title === null) {
      title = string(textContent(node));
    } else if (node.tag === "html") {
      language = string(node.attrs.get("lang") || node.attrs.get("xml:lang"));
    } else if (
      node.tag === "link" &&
      (node.attrs.get("rel") ?? "").toLowerCase().split(SPACE).includes("canonical")
    ) {
      canonical = canonical || safeUrl(node.attrs.get("href") ?? "", base) || null;
    } else if (node.tag === "script" && article === null) {
      article = readJsonLd(node);
    }
  }
  return {
    title: fields.get("og:title") || title || string(article?.headline),
    author: fields.get("author") || authorName(article?.author),
    description:
      fields.get("description") || fields.get("og:description") || string(article?.description),
    language: language || string(article?.inLanguage) || fields.get("og:locale") || null,
    publishedTime:
      fields.get("article:published_time") || fields.get("date") || string(article?.datePublished),
    url,
    canonicalUrl: canonical,
  };
}

function localAuthor(node: Node): boolean {
  if (
    node.attrs.get("itemprop") === "author" ||
    (node.attrs.get("rel") ?? "").split(SPACE).includes("author")
  ) {
    return true;
  }
  return (node.attrs.get("class") ?? "")
    .toLowerCase()
    .split(SPACE)
    .some((token) => ["byline", "author", "p-author"].includes(token));
}

export function refineMetadata(metadata: Metadata, selected: Node[]): Metadata {
  let heading: string | null = null;
  let author = metadata.author;
  let published = metadata.publishedTime;
  for (const root of selected) {
    for (const node of walk(root)) {
      if (node.tag === "h1" && heading === null) {
        heading = string(textContent(node));
      }
      if (author === null && localAuthor(node)) {
        author = string(textContent(node));
      }
      if (
        published === null &&
        node.tag === "time" &&
        node.attrs.get("itemprop") !== "dateModified"
      ) {
        published = string(node.attrs.get("datetime")) || string(textContent(node));
      }
    }
  }
  return {
    ...metadata,
    title: heading || metadata.title,
    author: metadata.author || author,
    publishedTime: metadata.publishedTime || published,
  };
}
