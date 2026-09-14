# Constellation integration 0.1.0-alpha.3

Author a local objective and read one exact saved-check result beside it.
This profile connects Maude, Monitor, Nightshift, NQ, an explicitly enrolled
application reader and AG-hosted Phosphor. No model credential is needed.

Start with [the pinned guide](https://unpingable.com/constellation/releases/0.1.0-alpha.3/guide.html).
It builds public sources, creates disposable local state, and inspects fresh,
expired and missing evidence. Expect an intentionally failed saved check—not
an objective-completion or permission verdict. The guide includes exact
post-run inspection, diagnostic retention and cleanup boundaries.

- Profile: `objective-saved-check-read/v1`.
- Tested environment: Linux x86-64, Ubuntu24.04.4, Rust1.94.0, Python3.12.3.
- Exact source, example and public Python dependency pins: `manifest.json` and
  `python-requirements.txt`; scoped evidence: `qualification.json`.
- Component versions remain independent. The example kit and AG runtime use
  separate commits; downloading a later kit does not upgrade the runtime.
- This is a finite local example, not an installed monitoring service. Local
  notification delivery does not establish human receipt.
- No AG/Docket effect, review, permission, full application migration, retention
  rollover, restore/rollback, general ECAD readiness or federation is qualified.

Existing alpha.1 consultation and alpha.2 saved-check releases remain unchanged.
Alpha identifies an exercised composition, not a stable support commitment or
family-wide maturity. Support is best effort with no guaranteed response time.
