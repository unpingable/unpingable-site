# Constellation

Constellation is an experimental system for checking automated work against
independent evidence. A worker saying “done” is a report, not proof that the
intended change happened. Constellation separates observation, permission to
act, execution and verification, and keeps uncertain outcomes explicitly unknown.

This repository is the public documentation entry point. The implementation lives
in the component repositories below.

## What works today

A bounded, participant-installed candidate has been exercised through a supervised
local cycle: observe a service, evaluate a proposed action, authorize one attempt,
execute it, then collect fresh evidence before recording completion. Refusals and
uncertain outcomes remain visible. Selected component demonstrations also show
reconciliation when an operation's result is initially unknown.

This is experimental software, not a general-availability release. Qualification
applies to exact candidates and bounded procedures, not arbitrary combinations of
repository heads. Seven-day unattended hosting and an independent human usability
study remain unqualified. Source publication does not enroll a machine, grant
permission to act, or provide a hosted service.

## Components

| Component | Role |
|---|---|
| [NQ](https://github.com/unpingable/constellation-nq) | Records evidence and evaluates narrowly defined questions; refuses when required evidence is unavailable. |
| [Agent Governor (AG)](https://github.com/unpingable/constellation-ag) | Decides whether one exact action may proceed under an enrolled grant. |
| [Docket](https://github.com/unpingable/constellation-docket) | Tracks an authorized execution attempt and its outcome, including uncertainty. |
| [Nightshift](https://github.com/unpingable/constellation-nightshift) | Tracks recurring work, changing conditions and matters needing attention. |
| [Monitor](https://github.com/unpingable/constellation-monitor) | Presents evidence published by the components without granting new authority. |
| [Linear Accountant](https://github.com/unpingable/constellation-linear-accountant) | Records bounded model use and its accounting where a workflow uses a model. |
| [Standing](https://github.com/unpingable/constellation-standing) | Represents the conditions under which work remains eligible. |
| [Continuity](https://github.com/unpingable/constellation-continuity) | Carries evidence across supported continuity boundaries without renewing authority. |

Workbench is the participant-facing inspection interface. Its repository remains
private while historical operator material is reviewed for publication. [Maude](https://github.com/unpingable/maude)
and [Switchyard](https://github.com/unpingable/switchyard-runtime) provide optional
planning and provider-runtime support; not every workflow requires them.
Each repository supplies its own license and dependency notices.

## Read, follow or participate

- [Project website](https://unpingable.com/constellation/): explanation and demonstrations.
- [Recorded terminal cycle](constellation/visuals/CYCLE.md),
  [refusal example](constellation/visuals/EARLIER-REFUSAL.md) and
  [diagrams and screenshots](constellation/visuals/README.md): sanitized records
  from an earlier local exercise, not a live service or current installation guide.
- [Documentation source](constellation/): component map, scope and operating guides.
- [Operator documentation](constellation/combined-candidate/README.md): prepared
  package context and recovery guidance. Older candidate identities in these
  documents are not an invitation to install or a public download offering.
- [Project questions and supervised-trial interest](https://github.com/unpingable/unpingable-site/issues):
  describe your use case without posting credentials or private operational data.
  Participation requires a separate arrangement with the maintainer; expressing
  interest does not authorize installation or execution.

Supervised participants receive the exact installation packet privately. No
centrally hosted runtime, public service endpoint or unrestricted beta enrollment
is offered here. Component issues and commits are the place to follow source work.

## Documentation publication

`dev/operator-beta` is the current documentation branch. GitHub Pages serves a
separately published `main` snapshot at [unpingable.com](https://unpingable.com/).
Publishing this branch makes source and documentation available on GitHub; it does
not deploy the website or distribute the sealed participant archive. Historical
release snapshots retain their original identities and limits.
