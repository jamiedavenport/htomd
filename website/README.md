# htomd website

Six Markdown pages, built with Blume and served by Cloudflare Workers Static
Assets at https://htomd.dev. Edit `content/`; shared behavior comes from Python,
and language-specific APIs come from each implementation. The SVG marks reuse
`../assets/icon.svg`, with a white variant for dark backgrounds.

## Develop

From the repository root, install the tools with `mise install`. Then:

```sh
cd website
bun install --frozen-lockfile
bun run dev
```

`bun run build` creates `dist/`; `bun run preview` serves that build. To check
Cloudflare's asset routing locally, run `bun run wrangler dev` after building.

CI installs locked dependencies and builds the website. It does not deploy.

## Deploy manually

Authenticate once with the JXD Cloudflare account:

```sh
bun run wrangler login
bun run wrangler whoami
```

Check that the account matches `account_id` in `wrangler.jsonc`, then:

```sh
bun install --frozen-lockfile
bun run deploy
```

The deploy script builds fresh static output before running Wrangler. A failed
build stops deployment. Credentials stay in Wrangler's local configuration;
never commit tokens or environment files. Public `workers.dev` and version
preview URLs are disabled.

To recover a previous site, check out a known-good revision in a separate Git
worktree, install its locked dependencies, and run the same deploy command.

## One-time domain setup

The `htomd.dev` zone already uses Cloudflare. Inspect existing DNS records and
redirect rules before setup; preserve unrelated records, including email DNS.

1. Deploy `htomd-docs`. Its Wrangler custom-domain configuration binds
   `htomd.dev` and provisions HTTPS through Cloudflare. Resolve any conflicting
   apex record deliberately before proceeding.
2. Add a proxied DNS record for `www`: type `A`, value `192.0.2.1`. It only needs
   to reach Cloudflare's redirect rule, not an origin server.
3. Add a **Single Redirect** matching `http.host eq "www.htomd.dev"`. Use a
   dynamic target of `concat("https://htomd.dev", http.request.uri.path)`, status
   **301**, and enable **Preserve query string**.
4. Ensure HTTP requests to the apex redirect to HTTPS, using Cloudflare's
   **Always Use HTTPS** setting if appropriate for the zone. Confirm that edge
   certificates cover both hostnames.

After deployment, check the homepage, a language page, and a nonexistent route
(which must return 404). Verify that both HTTP and HTTPS `www` requests redirect
to the apex with their path and query string intact:

```sh
curl -I 'https://www.htomd.dev/python/?source=check'
curl -I 'http://www.htomd.dev/python/?source=check'
curl -I 'http://htomd.dev/python/'
curl -I 'https://htomd.dev/does-not-exist'
```

Also check search, mobile navigation, light/dark themes, canonical URLs,
`sitemap.xml`, `robots.txt`, and `llms.txt`.

References: [Blume deployment](https://useblume.dev/docs/deployment),
[Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/get-started/),
and [custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/).
