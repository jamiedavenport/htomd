# HTML fixtures

115 pages from 29 domains: provisionally 65 articles, 30 documentation pages,
and 20 boundary cases. The domain split is 80 development/35 held-out pages;
replace a held-out domain before tuning on its failures.

Snapshots are sanitised; original downloads stay outside the repository.
The manifest records both hashes, removals, source credits and licence terms.
Update annotations and expectations alongside snapshots. Tests run offline.

- `annotations.json` and `annotations/`: unreviewed block inventories. Review
  content, order, exclusions, formatting, and metadata before marking approved.
- `curated.json`: 20 curated regression cases.
- `captured/`: 40 exact outputs for change detection, not reviewed ground truth.
  Markdown is stored as `.txt` to avoid loading remote images in GitHub previews.

Retain [NOTICE.md](../NOTICE.md), [LICENSES.txt](../LICENSES.txt), and the manifest
when copying fixtures or outputs. Source licences apply separately from MIT.
Review permissions and remove embedded code/assets before adding new snapshots.
