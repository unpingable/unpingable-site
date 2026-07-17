# PLS — plain-language summaries (genre rules)

**Status:** DRAFTS. Nothing in this directory is published or linked; pages
graduate out of here one at a time, each through its own coherence check.
Pivot named by the operator 2026-07-16 (browser-tab intake, ChatGPT-assisted
drafting; operator selects, this repo records).

## The genre

One PLS per public tool. Each one:

1. **Starts from a thing people already do.** Not from the ontology. The
   reader is already asking an AI what's happening on their server, already
   merging the PR, already trusting the dashboard. Meet them there.
2. **Exposes the missing layer without the ontology tour.** The pitch is the
   *boundary* the existing practice lacks, stated in the reader's own
   vocabulary. No constellation vocabulary imports — the lexicon is for
   people who click deeper (glossary.html exists for a reason).
3. **Kills the category error early, in one sentence.** Every tool has one
   predictable misreading ("oh, it's a smarter dashboard reader" / "oh,
   it's a linter" / "oh, it's LangChain"). Name the error and shoot it
   before the reader finishes forming it. The killer sentence is the most
   important line in the piece — draft it first.
4. **Separates the four things the naive version blurs.** The ops example
   sets the template: what was observed / what was missing-stale-aggregated
   / what was inferred / what was merely pattern-matched. Every PLS should
   find its domain's version of this four-way split — it IS the product.
5. **Ends on what the claims can do that narrative can't:** survive
   automation, delegation, or dispute. "Show their work" is the closer, not
   the opener.

## Honesty constraints (inherited, non-negotiable)

- Launch-posture rules apply: Columbo, not Jobs. No grade inflation — a PLS
  describes what shipped, in the custody grade it actually holds
  (specimen ≠ operational; candidate ≠ ratified).
- The 20b coherence discipline applies at graduation: a PLS page goes live
  only after a sweep confirms it against the repo it describes, at a named
  cut. Copy drift against reality is the same defect class as stale
  portfolio stubs.
- Exit-code semantics, NQ-optionality, and the two-seam approval split have
  bitten before (20b findings F1–F7). Check them every time.

## Roster (candidates, not commitments)

| Tool | The existing practice it starts from | The category error to kill | Status |
|---|---|---|---|
| NQ | "ask an AI what's happening on this server" | *a smarter dashboard reader* | drafted — `nq-ops.md` |
| AG | "let the agent apply its own edits" | *a linter / a firewall for prompts* | tab-intake pending |
| spine | "search the docs / ask the wiki" | *a search engine or CMS* | tab-intake pending |
| porter | "run the script on the box" | *an SSH wrapper* | tab-intake pending |
| verifier | "the policy engine says yes" | *another OPA* | tab-intake pending |
| nightshift | "cron with an AI attached" | *an autonomous agent scheduler* | tab-intake pending |

Rows are added as tabs land. A row is not a promise to publish.
