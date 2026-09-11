export interface Metadata {
  readonly title: string | null;
  readonly author: string | null;
  readonly description: string | null;
  readonly language: string | null;
  readonly publishedTime: string | null;
  readonly url: string | null;
  readonly canonicalUrl: string | null;
}

export interface Diagnostics {
  readonly strategy: "semantic" | "scored" | "fallback" | "none";
  readonly notes: readonly string[];
}

export interface Document {
  readonly markdown: string;
  readonly metadata: Metadata;
  readonly diagnostics: Diagnostics;
}

export interface ExtractOptions {
  readonly url?: string | null | undefined;
}
