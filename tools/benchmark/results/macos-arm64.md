# Benchmark measurements

Measured 2026-09-09 on Apple M5 Max (arm64, 36 GiB RAM), macOS-26.5.1-arm64-arm-64bit-Mach-O, Python 3.14.7. 115 offline sanitised pages, 12.82 MiB input. Single-threaded; five fresh rounds. Relative speed = competitor time / htomd time; above 1 means htomd is faster.

| Library | Conversion implementation | Extra Python packages |
| --- | --- | ---: |
| htomd | Pure Python / stdlib HTMLParser | 0 |
| markdownify | Python / BeautifulSoup + stdlib HTMLParser | 4 |
| html2text | Pure Python / stdlib HTMLParser | 0 |
| trafilatura | Python + native C via lxml | 16 |
| html-to-markdown | Rust core / Python bindings | 0 |
| htmd-py | Rust core / Python bindings | 0 |

| Library | Corpus seconds | Round median range (s) | Pages/s | Input MiB/s | Relative speed |
| --- | ---: | ---: | ---: | ---: | ---: |
| htomd 0.1.0 | 1.260 | 1.245–1.283 | 91.3 | 10.17 | 1.00× |
| markdownify 1.2.3 | 2.443 | 2.418–2.465 | 47.1 | 5.25 | 1.94× |
| html2text 2025.4.15 | 1.262 | 1.239–1.271 | 91.1 | 10.15 | 1.00× |
| trafilatura 2.2.0 | 3.257 | 3.238–3.312 | 35.3 | 3.94 | 2.58× |
| html-to-markdown 3.12.2 | 0.217 | 0.216–0.226 | 529.6 | 59.02 | 0.17× |
| htmd-py 0.1.2 | 0.163 | 0.162–0.167 | 705.4 | 78.62 | 0.13× |

| Library | Peak RSS MiB | Import ms | Wheel KiB | Installed MiB |
| --- | ---: | ---: | ---: | ---: |
| htomd | 127.59 | 14.65 | 18.98 | 0.05 |
| markdownify | 174.22 | 58.61 | 15.36 | 0.78 |
| html2text | 81.25 | 9.18 | 33.84 | 0.10 |
| trafilatura | 257.05 | 276.78 | 148.35 | 58.21 |
| html-to-markdown | 131.98 | 10.71 | 6728.10 | 15.05 |
| htmd-py | 104.70 | 0.53 | 451.00 | 1.08 |

Dependency counts include all installed direct and transitive runtime packages, excluding the library itself, interpreter and installer tools. No optional extras were selected. Counts come from the saved isolated installations. Bundled native code and Rust/C libraries are not counted as Python packages: zero package dependencies does not mean pure Python.

Defaults perform different work: htomd.convert() selects content and extracts metadata; Trafilatura extracts main content with Markdown output selected. markdownify, html2text, and htmd-py convert markup; html-to-markdown returns content and metadata with its defaults. Output size and extraction coverage differ. These timings do not measure output quality.

Source revision: `8f7c57f1d0487fb8dcf32e0cc2a5f4930601c8e9`; dirty: `True`. Exact source, harness, wheel, lock and corpus hashes are in the adjacent JSON.

## Reproduction

See [benchmark instructions](../README.md). Regenerate this report and the README from saved JSON with `mise run benchmark:report`.

## Failures and output diagnostics

Empty output is recorded separately from exceptions and is not a quality score. Incomplete timing rounds never receive complete-corpus throughput or ratios. Memory/import medians use successful workers; counts below expose missing samples.

### htomd

Adapter: `htomd.convert(html)`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 2,683,409 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `htomd==0.1.0`.

Wheel: `htomd-0.1.0-py3-none-any.whl`; SHA-256 `0abef3441e54efd34259e5133d637373ecb66c6fd3940fb340aab606cdc9053f`.

### markdownify

Adapter: `markdownify.markdownify(html)`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 4,040,910 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `beautifulsoup4==4.15.0`, `markdownify==1.2.3`, `six==1.17.0`, `soupsieve==2.9.2`, `typing_extensions==4.16.0`.

Wheel: `markdownify-1.2.3-py3-none-any.whl`; SHA-256 `a189a0bedfd14009030fde5f85bb6f77c56897cb839b5c25315dd7d4e3e290ba`.

### html2text

Adapter: `html2text.html2text(html)`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 4,073,201 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `html2text==2025.4.15`.

Wheel: `html2text-2025.4.15-py3-none-any.whl`; SHA-256 `00569167ffdab3d7767a4cdf589b7f57e777a5ed28d12907d8c58769ec734acc`.

### trafilatura

Adapter: `trafilatura.extract(html, output_format='markdown')`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 1,380,836 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `babel==2.18.0`, `certifi==2026.7.22`, `charset-normalizer==3.5.1`, `courlan==1.4.0`, `dateparser==1.4.3`, `htmldate==1.10.0`, `jusText==3.0.2`, `lxml==6.1.3`, `lxml_html_clean==0.4.5`, `python-dateutil==2.9.0.post0`, `pytz==2026.3.post1`, `regex==2026.9.3`, `six==1.17.0`, `tld==0.13.2`, `trafilatura==2.2.0`, `tzlocal==5.4.4`, `urllib3==2.7.0`.

Wheel: `trafilatura-2.2.0-py3-none-any.whl`; SHA-256 `ac43592a6201264dfc4f9c361cbe3eb3fea96e54437010a159d5e7365360ed98`.

### html-to-markdown

Adapter: `html_to_markdown.convert(html).content`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 4,109,708 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `html-to-markdown==3.12.2`.

Wheel: `html_to_markdown-3.12.2-cp310-abi3-macosx_11_0_arm64.whl`; SHA-256 `24a1853eb9d6f71187b94c7e6bddcc0563f3e24b8f4c289ba211f7b32d47535a`.

### htmd-py

Adapter: `htmd.convert_html(html)`; all other options default.

Complete timing: True. Successful RSS workers: 3/3; successful import workers: 20/20. First warm-up output: 4,756,859 characters. Empty documents across timing passes: 0.

Errors: none.

Workers with stderr: 0; full text retained in JSON.

Installed packages: `htmd-py==0.1.2`.

Wheel: `htmd_py-0.1.2-cp314-cp314-macosx_11_0_arm64.whl`; SHA-256 `9cf7b9afc4f7a39c117ac26ac4d5dfa11f11bb0c9fd3aada587d612bc0822e3f`.
