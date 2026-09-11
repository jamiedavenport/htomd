import { defineConfig } from "blume";

export default defineConfig({
  title: "htomd",
  description: "Extract Markdown and metadata from HTML in Python, TypeScript, Go, and Rust.",
  content: { root: "content" },
  deployment: { output: "static", site: "https://htomd.dev" },
  logo: {
    image: { light: "/icon.svg", dark: "/icon-dark.svg", alt: "htomd" },
    text: "htomd",
  },
  github: { owner: "jamiedavenport", repo: "htomd", dir: "website" },
  navigation: { sidebar: ["/", "/python", "/typescript", "/go", "/rust", "/cli"] },
  feedback: false,
});
