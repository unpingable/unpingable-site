# unpingable.com

Public documentation for the unpingable research program and the Constellation
family of tools.

The current Constellation integration release is
[`0.1.0-alpha.6`](https://unpingable.com/constellation/releases/0.1.0-alpha.6/guide.html).
Start at the [Constellation front door](https://unpingable.com/constellation/)
for the human-readable walkthrough, component map, integration guidance, and
the explicit limits of the qualified profile.

## Publishing

GitHub Pages serves `main` from the repository root at
<https://unpingable.com/>. The files under
`constellation/releases/0.1.0-alpha.6/` are an immutable release snapshot; do
not rewrite them to update the mutable site.

Before publishing mutable documentation, run:

```sh
python3 tools/render_constellation.py --check
python3 tools/render_constellation_meta.py --check
python3 tools/render_status.py --check
python3 tools/check_constellation.py
xmllint --noout sitemap.xml
git diff --check
```

The site contains public documentation only. Private campaign records,
credentials, retained provider material, and local inventory data do not
belong in this repository.
