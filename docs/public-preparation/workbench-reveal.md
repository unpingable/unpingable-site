# Workbench public presentation preparation

Locally prepared, not published. No push, merge, server, browser, backend, installer, or production action was performed by this lane. Root owns capture, asset custody, independent acceptance, adoption, and publication decisions.

## Source and adoption boundary

- Source site revision: `c38e5d7ef9ea8d0eacf0dce7d3fd04088c080e03`.
- Isolated worktree: `/data/git/.worktrees/site-workbench-reveal-20261005`.
- Branch: `lane/workbench-eda-reveal-v1`.
- Original `/data/git/unpingable-site` remains untouched. Its dispatch-time HEAD matched the source revision; seven tracked modifications were observed (`about.html`, `constellation.html`, `glossary.html`, `index.html`, `limits.html`, `status.json`, `tools/render_status.py`), plus untracked `design-review/` and `tools/__pycache__/`.
- Adoption must reconcile those mainline changes, including public claims, rather than overwrite the original tree.
- Owner inputs for existing generated status and component bodies were not changed. Navigation around the generated component block was changed; renderer checks verify it remains current.

## Qualification claim sources and limits

The authorized Phase C dispatch from root is this lane's claim input. It reports Phase A `CURRENT_FORWARD_LIVE_EDA_DIAGNOSTIC_LOOP_ESTABLISHED` and accepted Phase B `ORCHESTRATED_APPLICATION_TIER_5_OBSERVATION_AND_DIAGNOSIS_ESTABLISHED`. The exact accepted evidence identities below were supplied by root and the acceptance-record hashes were verified locally; this prose page does not replace acceptance records.

- A acceptance: `/data/git/.lanes/workbench-reveal-campaign/a8fab4e7-17fa-40b3-9c18-f66b18a07a00/phase-a/ACCEPTANCE.json`, SHA-256 `48908ffc88826d4802fbec1dd6716ed4061038376441eb3b74da1467f7c62512`; Workbench source `ff55c0600399a5d3c21b937570334bf629cb22b9`; VM run `d05ebd30-f5e7-41dd-8b4b-00d96ba17403`.
- B acceptance: `/data/git/.lanes/workbench-reveal-campaign/a8fab4e7-17fa-40b3-9c18-f66b18a07a00/phase-b-successor/ACCEPTANCE.json`, SHA-256 `7b70b87a85c07c04815f7a210066a0bd0d8ff62b25c765851d9e29e053cafc5a`; run `c72e8f44-4a23-4c0f-84fe-49edf23cb58f`; product `eea7f4664529a511e7de89c244d1296f5ac79830`; Monitor `6cc7d00a1f9a5979b917fe50540e4bf1d5310d5a`.

A: one fresh native unit Start, nine Workbench HTTP actions, zero operator CLI handoffs, one AG authorization spend, one Docket execution attempt, an independent postcondition, and continued local VM use.

B: a three-node k3d/k3s frontend → API → SQLite application, nine fault conditions, 72 cohort read attempts, 69 owner responses, three source refusals, 18 remediation-plan refusals, zero Kubernetes product remediation. No real node boot, DiskPressure, or full Level 3 claim. The earlier 1,000-case soak (486 good, 351 correct refusal, 163 correct indeterminate, zero failure) is a different campaign, not B throughput. No all-components claim. Linear Accountant's separate current model-decider use is not represented as participation in this demonstrated loop.

## Presentation assets and remaining preparation

`workbench-gallery.json` names the eight reserved captures and captions. The HTML gallery markers intentionally contain no images until reviewed campaign-owned captures arrive. No fake screenshot, broken image, or substitute browser capture is supplied. Root inserts the reviewed gallery and packages the read-only retained demo at `constellation/demo/index.html`; all demo links are relative to this page. Every figure caption must identify captured-record replay with presentation polish, not live production. The stylesheet supports a two-column gallery and one-column narrow display.

The page uses a charcoal/bone/amber palette with muted blue, green, and oxide from `operational_ecad/presentation.py`, structural rules, an editorial serif hierarchy, and system fonts. It adds no font network dependency or script. The three depths, six qualification tiers, and campaign intensity remain separate axes. Operational EDA is presented as an analogy and direction, not an established mature industry category.

## Formalization consideration

Decision owner: root campaign acceptance owner. Proposition: the public description must imply no broader operational authority or qualification than the accepted A/B cases, and the replay must not imply current live observation. Scope: this static presentation and its captions, not runtime correctness. Source identity: site `c38e5d7ef9ea8d0eacf0dce7d3fd04088c080e03` plus root Phase C dispatch; result identity: the lane commit named in its immutable COMPLETE notice.

Counterexamples/unknowns: equating diagnosis with remediation authority; describing k3d application cases as real node boot or DiskPressure coverage; equating soak intensity with tier; implying all components were exercised; displaying replay as a live panel; claim correspondence remains subject to root independent acceptance. Practical claim review, generated-source checks, link validation, and independent inspection suffice for this bounded static editorial change. No new runtime property or transfer rule is introduced; a formal model would not establish correspondence between prose and the accepted evidence better than the owning review. Future runtime authority claims remain subject to their own formalization consideration.

## Local validation and storage custody

The two existing checker unit tests pass; both existing generated-source checks pass; `git diff --check` passes. Before root asset packaging, the local link checker reports three references to the single expected absent destination `constellation/demo/index.html`. This is an explicit preparation dependency and blocks publication readiness. Root must rerun the checker after packaging and inspect the complete page at desktop and narrow widths.

Storage owner: root campaign. Worktree source allocation estimate <50 MiB, measured initial apparent size 322,084 bytes. Admission: root free 95,085,297,664 bytes / 55,595,851 free inodes; /data free 798,866,370,560 bytes / 120,779,199 free inodes. Both exceed the fixed 60 GiB reserve. No large producer, compiler output, VM, cache, SSH identity, or detached execution is created by this lane. Other host consumers are outside lane authority and were not attributed. Worktree source is retained for review/adoption and unique commit custody; disposition belongs to root after adoption and receipt dependency review. Completion notice records final allocated bytes and capacity; concurrent host allocation prevents attributing capacity deltas solely to this work.
