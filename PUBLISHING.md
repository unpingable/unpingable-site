# Updating the public site

`status.json` is the authoritative record for the mutable homepage project descriptions, Constellation introduction/status/release notice, ABSD cross-reference and dated ledger. Change its `current`, `absd`, `as_of` and relevant ledger rows together. Acceptance, human evaluation, availability and release are separate fields: approval for evaluation does not imply a beta release or a public download. Cite evidence and identify older snapshots explicitly. Historical records remain dated; files beneath `constellation/releases/` are immutable snapshots and are never generator targets.

From the repository root:

```sh
tools/publish-site.sh generate
tools/publish-site.sh check
python3 tools/qualify_site_content.py
tools/publish-site.sh diff
tools/publish-site.sh preview
```

Preview `/`, `/constellation/`, `/constellation/status.html` and `/constellation/absd.html`; stop the preview server after review. Check the diff, commit the record and generated HTML together, then place the reviewed commit on the local `main` branch and run `tools/publish-site.sh publish` to publish the reviewed commit to `origin/main` using the existing GitHub Pages deployment from the main branch repository root. Confirm the Pages deployment source revision and the live routes. Do not merge operator-development machinery to update public copy. Generated blocks require exactly one marker pair; `--check` fails if any generated surface is stale. A release notice is rendered from the same record, not maintained in a second release page.

The composition verifier is a separate immutable-release qualification tool requiring exact pinned external component checkouts; ordinary mutable-copy publication does not requalify historical releases.
