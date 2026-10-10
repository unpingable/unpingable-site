# Prepared stranger-operability exercise — not executed

This exercise is prepared and has not been run; no human evidence exists for this candidate.

Constellation watches one systemd unit's state and, when current evidence shows it down, an operator can request one fixed Start of it, which runs only after an explicit one-use grant is spent; [What this is](README.md#what-this-is) explains it. Nothing in this exercise starts the unit automatically: the remediation consumer is installed disabled and is not enabled here.

Release-approver review precedes the separately admitted human study. Participant: competent Linux operator who has not worked on Constellation. Give only the supplied candidate archive and its release record, checksums, Workbench, operator docs and a fresh Ubuntu 22.04 VM. No source checkout, Cartography, architecture briefing, campaign records or silent agent repairs. Record exact candidate hash and participant/setup identities before starting.

This study selects [Installation’s manual alternative](INSTALLATION.md#manual-alternative-and-human-study), not the primary nginx try path. The facilitator supplies a separate fresh VM. The facilitator does not supply or pre-create the harmless sleep-unit fixture: the participant's enrollment step (`scripts/enroll-local-fixture.py`) creates, enables and starts `constellation-beta-http-fixture.service` itself, and its code refuses when that unit file already exists, so a pre-created unit blocks enrollment (that refusal was not exercised). Do not run `try/` on that VM. Apply and verify the documented persistent port 8081 loopback restriction before enrollment; the API still binds all interfaces and its GET reads remain unauthenticated. No production notification, model/provider credential or important application fault is needed. The supplied upgrade fixture uses an actual ordinary Workbench package version change with identical runtime bytes; record this limit transparently. Enrollment is the participant's explicit bounded one-use action choice, not an automatic package effect.

| Step | Participant outcome | Score / evidence |
|---|---|---|
| 1 | Obtain the supplied exact candidate; check bytes and explain what the supplied identity channel does and does not authenticate | pending |
| 2 | Install source-free packages and inspect dependency health | pending |
| 3 | Explicitly enroll the fresh bounded fixture | pending |
| 4 | Enter through Workbench at the documented address | pending |
| 5 | Explain current unit state, native gaps and HTTP not instrumented | pending |
| 6 | Inspect exact package/build/source identity | pending |
| 7 | Understand facilitator-controlled harmless unit stop | pending |
| 8 | Distinguish diagnosis from admissible governed Start | pending |
| 9 | Recover via documented native API; inspect the settlement outcome and the independent postcondition, and say which of the two AG `completed` reflects | pending |
| 10 | Upgrade Workbench package .1 to the exact supplied .2 fixture; inspect package and unchanged runtime identities | pending |
| 11 | Encounter a bounded collector/currentness failure with the fixture otherwise intact | pending |
| 12 | Recover collection and roll Workbench .2 back to .1 with retained recovery records | pending |
| 13 | Confirm fresh same-boot unit state, final identities and retained attempts | pending |

Steps 10–13 stay on the same enrolled VM. Use UPGRADE-FIXTURE.json and the day-two commands: Workbench package .1 → .2 → .1. The ordinary Debian package version changes; source and runtime payload do not. This tests package upgrade/restart/rollback usability without replacing NQ admission, renewing a grant or claiming a new semantic generation. An automated check verified the inert nine-package NQ 0.2.4 spine → NQ 0.2.5 path for the predecessor candidate's NQ package, not for the NQ package in this candidate; no such path is verified here. That NQ 0.2.4 predecessor remains separately protected historical recovery custody, excluded from this candidate, and is not substituted into the active human enrollment.

**This download contains no deliberately bad upgrade fixture.** It supplies a Workbench package pair with identical runtime payload (upgrade and rollback of the package version only) and a facilitator collector stop (step 11). On a qualification guest of this package set (an earlier assembly of this candidate with the same packages and scripts), an agent-driven lab run on the manual path and not human evidence, the two packages' extracted payloads were identical, both directions returned `dpkg` exit 0 with an empty audit, and after the collector stop Workbench read `stale` (`source_or_evaluation_expired`) from 60 seconds on and `current` again after `sudo systemctl start nqd-ops.service`. No package in `packages/` or `upgrade/` fails to install, fails to start or changes runtime behaviour, and no step here produces a failed upgrade to recover from. The deliberately-bad-upgrade-and-rollback task named in the Beta Candidate 1 definition was accepted on an earlier package generation and cannot be exercised by a participant from this download. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive. The only bad-upgrade procedure mentioned in the archive is in `reference/`, which must not be used with this candidate ([known issues](KNOWN-ISSUES.md)).

For step 7 the facilitator stops only `constellation-beta-http-fixture.service`; it is a harmless sleep unit, despite its retained identifier. For step 11 the facilitator stops only `nqd-ops.service`, waits at least 65 seconds and asks the participant to interpret the native stale result. Do not modify the clock or truth records. Steps 9 and 12 must use the documented operation and recovery instructions. In both, recovered means fresh evidence that the unit (step 9) or the collector (step 12) is active again; the exercise does not observe application health. Setup assistance is recorded and cannot substitute for a participant step.

Score each step **obvious / reread required / docs search required / hint required / blocked**. Record UI→CLI handoffs, time, misunderstanding, docs/pages consulted, native results and hints. Need for unpublished knowledge is a product/usability defect. No invented aggregate numerical pass threshold substitutes for owner review. Preserve failures and rerun only affected steps after one bounded repair. Do not have an agent finish a blocked step for the participant.


Plan a supervised session of up to four hours and end it the same day. This candidate's NQ has a [finite capacity ceiling](KNOWN-ISSUES.md) with controlled refusal, and nothing here claims unattended operation. Pin this candidate's archive SHA256, from the release record beside the archive, and its package identities for the participant, not a prior archive. Pause on enrollment/action uncertainty, preserve the error and records, and follow [failure/session-end guidance](DAY-TWO-RUNBOOK.md#failed-or-interrupted-enrollment). No silent agent repair, record deletion or fresh enrollment counts as participant recovery.
