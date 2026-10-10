# Known issues

This candidate is for explicitly bounded, supervised sessions only. Plan a session of up to four hours and end it the same day. NQ issue #27 remains open. Nothing here claims unattended operation, and no human study has been run.

## AG `completed` does not mean the governed Start succeeded

AG's `complete` step requires one thing: a fresh observation of the enrolled unit active after settlement. It does not read the settlement outcome. On the `try/` and manual paths no other component applies a success rule, so AG can reach `completed` after a failed settlement when something else made the unit active.

Observed case, on the retired 8 October candidate: the unit was stopped and the steps through `authorize` were run; the unit was then started by hand between `authorize` and `dispatch`; then `dispatch`, `poll`, `continue` and `complete` were run. The executor refused with a prestate mismatch and no start job ran. The settlement was recorded as failure. AG still reached `completed` on the fresh active observation. One use of the one-use grant was consumed even though no start ran. Only this case was executed; that any failed Start followed by the unit becoming active some other way ends the same way follows from reading AG's code, not from a run.

The Workbench attempt line in this candidate prints `Remediation attempt: AG state <state>.` followed by exactly one settlement sentence taken from AG's settlement record:

- `Governed Start settled as success, <time>.`
- `Governed Start settled as FAILURE, <time>: the governed Start did not succeed.`
- `No settlement recorded: the governed Start has not been settled.`
- `Settlement outcome not readable from the retained AG records; nothing inferred.`
- `Settlement records disagree or are unreadable; nothing inferred.`
- `Settlement outcome is not available in this record; nothing inferred.` (an attempt summary written without a settlement field)

For `completed` it then prints: `AG state completed means the unit was observed active after settlement; it does not by itself mean the governed Start succeeded.`

**Read the settlement sentence, not the state name.** The unit status sentence (`nginx.service: active (running) …`) is a separate paragraph above the attempt line and still precedes a FAILURE sentence on the page. This display was tested against the recorded receipts of the observed case in Workbench's unit tests; whether it was exercised on a guest of this archive is stated in `QUALIFICATION.json` beside the archive.

**Run `poll` before reading the result.** `No settlement recorded: the governed Start has not been settled.` describes AG's record. Between `dispatch` and `poll` the executor and Docket may already have run and settled the Start; AG learns the settlement at `poll`. On qualification guests of this package set (an earlier assembly of this candidate with the same packages and scripts) the page showed this sentence after `dispatch` while the unit was already active again, and in the hand-started case while Docket had already settled the Start as failure. The sentence never claims success. All such guests were agent-driven lab runs, not human evidence. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive.

**`CURRENT_POSTCONDITION_REQUIRED` from `complete`** means no current observation of the unit active exists. Repeating `complete` helps only while waiting for the unit to become active after a Start. On an already completed attempt with the unit inactive it is the expected refusal, and repeating does nothing ([Operations](OPERATIONS.md#refusals-expiry-and-second-attempts)).

**A refused `continue` leaves a stray file.** On the manual-path qualification guest of this package set, the refused `continue` of a second attempt left a new `continuation-<id>.json` in `/var/lib/constellation-live-ecad/public/` naming an occurrence AG never created. It grants nothing and is not an AG record; nothing read it afterwards in that run.

**Attempt line wording when AG inspection is unavailable.** When AG inspection is unavailable but a retained AG settlement record exists, the attempt line reads `Remediation attempt: no AG campaign.` before the settlement sentence. The settlement sentence is the retained AG record; the `no AG campaign` wording is wrong. This does not show a failed Start as successful.

**One malformed retained action receipt removes the whole attempt line.** The page then shows the read gap (`FACADE_ATTEMPT_READ_UNAVAILABLE`) and the raw AG record rather than an outcome. This does not show a failed Start as successful either.

## NQ: bounded retention with a finite ceiling; issue #27 remains open

This candidate carries NQ with bounded retention (issue #27 remains open). Initialization and maintenance must use the same intended service limits and helper controls as collection. The packaged per-file limit is still 1 GiB; it is not an aggregate store budget. NQ persists an envelope derived from actual filesystem capacity/free space, an explicit reserve, auxiliary allowance and per-file limits. Ordinary restart neither enlarges nor shrinks it. Keep the configured seven-day target unless an explicit new admission changes policy; do not silently shorten it to make ingestion continue.

Expired history can be retired only when dependency-aware retention allows it. A protected finding or other custody dependency may hold the global prefix. Permanent idempotency identity commitments also remain charged to the finite store. Capacity refusal is an allowed result; preserve state rather than repeatedly restarting or deleting records. The installed NQ operator guide at `/usr/share/doc/nq-ng/OPERATIONS.md` describes the admitted initialization and maintenance boundary; it supplies no recovery from a capacity refusal.

**No documented way to inspect the envelope.** Neither these documents nor that guide name a command that prints the persisted capacity envelope or the latest report sequence. On the try-path qualification guest of this package set `status export` and `doctor`, each run once through the packaged `nq-ops-as-nq` wrapper, printed no envelope fields (the `status export` output did carry `max_report_sequence`); that single run is not a documented procedure. The guide is written for `nqd.service`, `/etc/nq/nq.toml` and `/var/lib/nq`. This candidate runs the separately enrolled `nqd-ops.service` with `/etc/nq/nqd-ops.toml` and `/var/lib/nq-ops`, so the guide's commands and paths do not apply as written, and its first paragraph links to a web address an offline VM cannot reach. Observed values, as initialised on that guest: per-file limit 1 GiB (`file_limit_bytes 1073741824`; `systemctl show nqd-ops` reported `LimitFSIZE=1073741824`) and retention horizon seven days (`horizon_seconds 604800`). The envelope values were read from a copy of the store by a method these documents do not give; they are stated as observed, not as a way to inspect.

What that means on this trial:

- **The store still grows.** The planning figure at this trial's 5-second collection cadence is about 27 MB per hour. It is derived, not measured as a rate: about 37 KB per collection, measured on this NQ package at component level, times 720 collections per hour. On the four-hour soak on a qualification guest of this package set the store grew about 24 MB per hour with no collector restarts.
- **The ceiling comes before any expiry.** With the packaged 1 GiB per-file limit the ceiling is reached after roughly 40 hours, before anything is seven days old. On this trial nothing expires and the seven-day retention target is never reached. The 40-hour figure is arithmetic from the planning figure; it was not observed.
- **At the ceiling** (derived from code reading and component-level runs, not exercised on a guest of this package set) the collector is expected to refuse new collections. Workbench is then expected to show `stale` (`source_or_evaluation_expired`) with an empty gaps list and not to name the cause; the journal of `nqd-ops` should (`journalctl -u nqd-ops`). `nq doctor` may still report healthy.
- **No same-VM recovery is supplied.** There is no resize command, and NQ's archive rollover does not work with this package's store format; its procedure document is not included in this candidate. Preserve the records you need and use a new VM.
- **Copy the store as three files, with the service stopped.** A graceful stop of `nqd-ops` leaves the `-wal` file in place. A copy of `nq.db` alone can lose the most recent commits. Stop `nqd-ops`, then copy `nq.db`, `nq.db-wal` and `nq.db-shm` from `/var/lib/nq-ops` together.
- **Restart or reboot at the ceiling** may leave the collector restarting in a loop. This was not tested.
- **What was exercised.** Expiry and capacity refusal were exercised only at component level, under different limits, never on this try path. On a guest, collection was observed for four hours, far short of the ceiling.
- **Session bound.** Plan a session of up to four hours and end it the same day, long before the ceiling. Basis: collection on this NQ package was observed continuously for four hours on one agent-driven guest; longer sessions are not covered. The one-use grant lifetime of two hours is a separate limit; grant expiry does not stop collection.
- **Open retention defects that a session of this length cannot reach.** This NQ package has the following known defects. All of them arise only after the first expiry, which is seven days out, and the size ceiling comes first, so none can be reached in a supported session: collections aborted by an expiry refusal; a cursorless read that receives no response after expiry; higher validation cost after the first expiry; and a `validated: full` report after expiry that overstates what was checked. They are tracked upstream as open and are not fixed here. This is why unattended or multi-day use is not supported.

Component qualification does not establish seven-day availability, arbitrary capture sizes, indefinite identity growth or human newcomer usability. Qualification of this exact archive is recorded in `QUALIFICATION.json` beside the archive.

## Host-posture keeps a 512 MiB file limit; do not use the reference path

`constellation-host-posture.service` is packaged with `LimitFSIZE=512M`, a 512 MiB per-file limit. This is an accepted, documented limitation. Neither the `try/` path nor the manual path starts that unit. With this NQ package a store initialised under the collector's 1 GiB limit cannot be opened under the 512 MiB limit; that statement is derived from code reading and component-level runs, not exercised on a guest of this package set.

The `reference/` installation path and `scripts/enroll-canary-observation.sh` initialise NQ outside the bounded wrapper and have not been run with this NQ package. Do not use them with this candidate. The `reference/` documents remain as historical reference only.

## Do not install over the 8 October candidate

The `nq-ng` version in this candidate, `0.2.5+qualification.retention.20261010.2`, sorts below the retired 8 October candidate's `nq-ng`, so installing it there is a downgrade. That candidate's store would also need an `nq admin upgrade`, which this candidate neither documents nor qualifies. Use a fresh VM.

## No automatic remediation is enabled

The remediation consumer is installed disabled. Nothing in the `try/` path or the manual path enables it, and no automatic remediation has been run on these packages. Every Start here is requested step by step by an operator.

The remediation package's description reads "Constellation bounded autonomous remediation consumer (v1)", and its installed README calls deterministic v1 the "reference/default remediation policy". Neither describes this candidate: here the consumer ships disabled, and autonomous remediation has not been demonstrated on these packages.

`scripts/enroll-canary-observation.sh` ships executable. It must not be run in a trial ([above](#host-posture-keeps-a-512-mib-file-limit-do-not-use-the-reference-path)).

## Unexercised sizes and paths

The qualification guests of this package set were Ubuntu 22.04 guests with 4096 MB RAM, 2 CPUs and a 20 GiB disk, offline; the try path ran with supplied nginx packages. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive. Other sizes, the online apt path and Multipass are unexercised.

The manual path's port 8081 restriction was probed only from inside the VM, over IPv4; reachability from another machine was not tested ([Installation](INSTALLATION.md#manual-alternative-and-human-study)). After session end and after package removal no reboot was made ([Day two](DAY-TWO-RUNBOOK.md#end-the-session)).

## No deliberately bad upgrade fixture

This download contains no deliberately bad upgrade fixture. It supplies a Workbench package pair with identical runtime payload (upgrade and rollback of the package version) and a facilitator collector stop. The deliberately-bad-upgrade-and-rollback task named in the Beta Candidate 1 definition was accepted on an earlier package generation and cannot be exercised by a participant from this download. The only bad-upgrade procedure the archive mentions is in `reference/`, which must not be used with this candidate.

## Workbench source declares a newer Python than the package needs

The Workbench source declares Python 3.11 or later for its development test suite, while the package depends on Python 3.10 or later; on a qualification guest of this package set (Python 3.10.12) all eleven installed modules were byte-identical to the source and the tests of the installed modules passed, while the full suite of 269 tests ended with 86 errors, 3 skips and no assertion failures: 44 errors come from Python 3.11-only APIs in modules that are not installed, 38 tests need Node.js, and 4 need a git checkout or other facilities the guest lacks.

## Predecessor history, retired 8 October archive: unbounded store (about 41 hours extrapolated)

These observations describe the NQ package in the retired archive SHA256 `0bdea16eea36a8e6b5dd2ccf0b511c8812008d6a1ec5f6ff811c6726ccc69070`, not this candidate's NQ package. They are kept so the earlier defect stays visible.

- The packaged `nqd-ops.service` sets `LimitFSIZE=1G`, a 1 GiB limit on any file it writes.
- NQ 0.2.5 stores about 36 KB on disk per collection and has no retention, compaction or automatic rollover, so the ops store only grows.
- At the exercise's 5-second collection cadence the store grew about 25.3 MB per hour (measured over one hour). Reaching 1 GiB in about 41 hours is an extrapolation from that rate, not a measurement. A different load of 10 watchers every 60 seconds was only extrapolated; its row sizes were not measured. This does not establish a general duration or per-session storage allowance.
- At the limit the kernel kills nqd and systemd restarts it without end. This was reproduced with the limit lowered to 65 MiB, not at 1 GiB: each restart ran about 8 s, died, waited 5 s and restarted, a cycle of about 16 s (11 kills in about 3 minutes). The journal shows `status=25/XFSZ`; NQ itself logs nothing about it.
- Workbench then shows the observation as `stale` (`source_or_evaluation_expired`). It does not name the cause, and its gaps list stays `[]`. Check `systemctl status nqd-ops.service` and its journal when evidence goes stale and does not come back.
- Restarting the service did not help. For that archive the documented recovery was NQ's operator-controlled archive rollover, which seals the full store and prepares a new store generation that must be enrolled again; it was not tried on a store wedged at the limit (the 65 MiB reproduction was recovered by removing the lowered limit). That rollover procedure document was bundled in that archive only. It is not included in this candidate, and the rollover command does not work with this candidate's NQ store format. On the local exercise, enrollment refuses to run twice, so in practice use a new VM.
- This kill-and-restart failure is the retired archive's behaviour. This candidate's NQ is expected to refuse at its ceiling instead, as described above (derived, not exercised on a guest), and its growth figures above are stated for its own package.

Historical growth rate and the kill-and-restart loop were measured on a fresh install of the earlier candidate's NQ during its preparation; the hour and day figures are extrapolations.

## A reboot restores units outside governance

An enabled unit (for example `nginx.service` on the `try/` path) is started by systemd at boot. Workbench then reads `current`, which describes the unit's state on the new boot, not a governed recovery. The status line then says `current boot` about the fresh observation. The attempt line under it, after the AG state and settlement sentences, says `Prepared in an earlier boot (…); the host is now in boot …` and that the current unit state is not evidence of the attempt; it names the preparation boot only, since the completion boot is not recorded. The enrollment boot is kept only by the native API on 8081 (`/api/enrollment`). The one-use grant stays spent.

## Native API records carry no unit-only disclaimer

The Workbench status line and cohort JSON say "Unit state only, not service health". The native API records on 8081, including `/api/enrollment`, do not; their nonclaims (for example `enrollment is not healthy baseline`) say nothing about HTTP. They are unit evidence only. The packaged replay pages `healthy-cohort.html`, `refusal.html`, `application-relationship.html` and `mixed-version.html` are recorded history and also show unit state only without saying so.
