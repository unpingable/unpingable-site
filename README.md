# unpingable.com

Public documentation for Constellation and related research. The current product
preparation is the [combined Operational EDA candidate](constellation/combined-candidate/README.md),
with source-free Ubuntu22.04 artifacts, Workbench and operator documentation.
It is a neutral owner-review candidate; BC1 is not tagged/published and the formal
stranger-human study is prepared, not executed. Alpha.6 remains an older immutable
released profile, not the current installation instructions.

## Operator path

[Overview](constellation/index.html) → [installation](constellation/combined-candidate/INSTALLATION.md)
→ [operation](constellation/combined-candidate/OPERATIONS.md) →
[day two](constellation/combined-candidate/DAY-TWO-RUNBOOK.md).
The eventual release directory supplies the archive, external checksum and
release page together. No source checkout or private architecture record is
required. Prepared download metadata does not claim public artifact availability.

## Source and website publication

`dev/operator-beta` is the canonical current documentation line. GitHub Pages
continues to serve the separately published `main` snapshot from the root at
https://unpingable.com/. Preparing/pushing this branch does not change Pages
or publish BC1. Preserve immutable `constellation/releases/` snapshots and the
byte-pinned historical reveal.

Before ordinary publication, run:

```sh
python3 tools/render_constellation.py --check
python3 tools/render_constellation_meta.py --check
python3 tools/render_status.py --check
python3 tools/check_constellation.py
xmllint --noout sitemap.xml
git diff --check
```

The site contains public-safe documentation only. Private host names, custody
paths, credentials and private tracker URLs do not belong in its operator path.
[Later beta planning](docs/BETA-WORK.md) does not activate future capabilities.
