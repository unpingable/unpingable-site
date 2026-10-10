# Try the candidate with nginx

This guide targets `constellation-canonical-candidate-20261010`, which carries NQ with bounded retention (issue #27 remains open). The candidate is prepared: not approved, not published, not distributed. Pin the SHA256 on the release record beside the archive (`ARTIFACT.json` and the `.sha256` file). The recorded 8 October cycle does not qualify this package set; qualification of this exact archive is recorded in `QUALIFICATION.json` beside the archive. The human newcomer study has not been run.

One command takes a fresh, disposable Ubuntu 22.04 amd64 VM to a Workbench that observes the packaged
`nginx.service` and offers one governed Start. Use a VM you will throw away. Do not use an existing
Constellation installation.

## Get a VM

Multipass on a laptop is one way to get a VM; it was not exercised. On a qualification guest of this package set
(an earlier assembly of this candidate with the same packages and scripts), the try path ran offline with supplied nginx
packages on Ubuntu 22.04 with 4096 MB RAM, 2 CPUs and a 20 GiB disk. All such guests were agent-driven lab runs, not
human evidence. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive. Other sizes and the
online apt path are unexercised:

```sh
multipass launch 22.04 --name try --cpus 2 --memory 4G --disk 20G
multipass transfer constellation-canonical-candidate-20261010.tar.gz constellation-canonical-candidate-20261010.tar.gz.sha256 try:
multipass shell try
```

## Run it

This directory ships inside the archive. Check the archive against the SHA256 in the identity record supplied with it, extract it and
run the script from the extracted directory. Online (the VM can reach the Ubuntu archive):

```sh
sha256sum --check constellation-canonical-candidate-20261010.tar.gz.sha256      # compare this hash with the supplied identity record too
tar --extract --gzip --file constellation-canonical-candidate-20261010.tar.gz
cd constellation-canonical-candidate-20261010
sudo try/try-constellation.sh --archive ../constellation-canonical-candidate-20261010.tar.gz \
  --sha256 "$(cut -d' ' -f1 ../constellation-canonical-candidate-20261010.tar.gz.sha256)"
```

`--archive` also accepts an https URL; the hash is always required and is checked before extraction.
Offline: add `--nginx-debs DIR`. Build that directory on any machine with apt, against jammy, from the
VM's own package list so only missing dependencies are fetched:

```sh
# on the VM:   cat /var/lib/dpkg/status > guest-status
# elsewhere (no root needed): an apt root whose sources.list names jammy, jammy-updates and jammy-security
# main with signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg, and Dir::State::status=guest-status
APT_CONFIG=./apt.conf apt-get update
APT_CONFIG=./apt.conf apt-get install --download-only -y nginx      # .debs land in Dir::Cache/archives
cd DIR && sha256sum *.deb > SHA256SUMS                              # checked by the script if present
```

For the stock jammy cloud image, in the earlier candidates' runs, that was 20 packages (nginx 1.18.0-6ubuntu14.21 and its libraries, 2.7 MB).

The archive's own Workbench (0.1.0+release.20261010.1) reads the governed unit from the enrollment request, and the
archive's RUNTIME-IDENTITIES.json describes it, so no other input is needed. `--help` also lists
`--workbench-deb`, `--workbench-sha256` and `--identity-override`: these are lab-only flags for testing a
different Workbench build and are not part of the normal try path. Earlier archive qualification used no replacement flags; consult `QUALIFICATION.json` beside this archive for the invocation used on it.

The script verifies the archive and its SHA256SUMS, installs nginx and the eleven candidate packages,
checks installed-SHA256SUMS, enrolls, waits for current observation and prints the Workbench address,
how to reach it from the laptop, and the command that breaks nginx. Earlier archive lab runs, offline, took 16 to 27 s; those timings are not a guarantee for this candidate. Consult `QUALIFICATION.json` beside this archive for its own run and limits.
It refuses to run twice on one VM.

## What is governed, and what is not

- The governed unit is the nginx package's own `nginx.service`, unchanged: no fixture unit, nothing masked.
  Enrollment refuses if that unit has drop-ins, is not enabled or is not active.
- Constellation observes **systemd unit state** for that unit. **Unit active is not service healthy.**
  HTTP health of nginx is not instrumented: the candidate's single-host enrollment has no HTTP watcher
  (its HTTP reader exists only for a separate controller host with a fixed endpoint). A stopped or
  crashed unit is visible; nginx answering 500s or hanging while its unit is active is not.
- Enrollment creates one Start capability for that unit and a Docket grant usable once, for two hours.

## The loop

Break nginx:

```sh
sudo systemctl stop nginx
```

Within seconds (2 to 16 s across five lab guests of the earlier candidate) Workbench (`/operator.html`, JSON at `/api/cohort`)
shows at the top `nginx.service: inactive (dead), observed N s ago, current boot. Unit state only, not
service health.` and the required-active claim
as `contradictory current_boot_claim_contradicted`, with the native summary "the system manager reports
the unit inactive in acquired boot ...". Recover through the native API, from the extracted candidate
directory (`/opt/constellation-try/constellation-canonical-candidate-20261010`), inspecting each result:

```sh
sudo python3 scripts/native-action.py prepare --identity operator-cli --prestate inactive --assessment 'Current native evidence shows the enrolled unit inactive; cause is not established.'
sudo python3 scripts/native-action.py init
sudo python3 scripts/native-action.py record-proposal
sudo python3 scripts/native-action.py require-standing
sudo python3 scripts/native-action.py decide
sudo python3 scripts/native-action.py authorize
sudo python3 scripts/native-action.py dispatch      # the only step that starts the unit; never repeat it
sudo python3 scripts/native-action.py poll
sudo python3 scripts/native-action.py continue
sudo python3 scripts/native-action.py complete
```

`--identity` is required by `prepare` and is recorded as the worker identity in the attempt (`/api/attempt`). Name
whoever actually drives it: `operator-cli` for a person at the command line; an agent-driven run must pass something
like `agent-preflight`.

Run `poll` before reading the result. Between `dispatch` and `poll` the attempt line still says `No settlement
recorded: the governed Start has not been settled.` That sentence describes AG's record: the executor and Docket may
already have run and settled the Start (on the qualification guest of this package set nginx was already active again at that point), and
AG learns the settlement at `poll`.

`complete` succeeds only on fresh current evidence that the unit is active again. `CURRENT_POSTCONDITION_REQUIRED`
means no current observation of the unit active exists; right after a Start, wait a few seconds and run `complete`
again (on the qualification guest of this package set the first `complete` succeeded and this wait was not exercised). Workbench then shows
the claim `current` and an attempt line that begins `Remediation attempt: AG state completed.` followed by one
settlement sentence. The settlement sentence is the result of the Start: `Governed Start settled as success, <time>.`
when it succeeded. `AG state completed` only means the unit was observed active after settlement. If the sentence
reads `Governed Start settled as FAILURE, …`, the governed Start did not succeed even though the state is `completed`;
this happens when something else made the unit active, for example a start by hand between `authorize` and `dispatch`,
and the grant use is consumed all the same ([known issues](../KNOWN-ISSUES.md)).

One attempt per enrollment. After the attempt completes, stopping nginx again and repeating `prepare` is
refused by Workbench's one-attempt guards (`ATTEMPT_ALREADY_EXISTS`, then `init` with
`CAMPAIGN_ALREADY_EXISTS`); `record-proposal`, `require-standing`, `decide`, `authorize` and `dispatch` are
refused by AG (`NATIVE_COMMAND_REFUSED:ag-loopctl`, exit 2). The receipts do not show AG's own refusal reason.
On the qualification guest of this package set all ten steps were tried: `poll` and `continue` were also refused with
`NATIVE_COMMAND_REFUSED:ag-loopctl`, and `complete` with `CURRENT_POSTCONDITION_REQUIRED`, each exit 2. On a completed
attempt with nginx stopped that last answer is the expected refusal; repeating `complete` does nothing. `recover`
answered exit 0 with `external_revalidation`. No start ran. The grant shows one recorded use; its own
one-use limit is not what refuses these, and the lab runs never reached it. Those refusals are
printed to the caller and kept on the guest
API (`curl -s 127.0.0.1:8081/api/attempt`). The attempt line under the Workbench status line ends with the last
request, e.g. `Last action request: dispatch refused, NATIVE_COMMAND_REFUSED:ag-loopctl, …`. Start nginx yourself
with `sudo systemctl start nginx`; a new governed exercise needs a new VM. "Recovered" here means the unit is observed active again, not that nginx serves requests.

## Keep it private

Workbench listens on the VM's loopback only. The native reader/action API
(`constellation-live-reader.service`) binds port 8081 on every guest interface. Its GET reads
(`/api/read`, `/api/attempt`, `/api/enrollment`) need no credential; only POST `/api/actions` needs the
operator token. Before enrollment the script installs a systemd drop-in,
`/etc/systemd/system/constellation-live-reader.service.d/loopback.conf` (`IPAddressDeny=any`,
`IPAddressAllow=localhost`), which persists across reboot. After enrollment it stops, and takes the
reader down, unless that drop-in is in force and a request to 8081 on each non-loopback address of the
VM fails. It also adds a non-persistent iptables rule dropping non-loopback traffic to 8081, as a
second layer only. nginx itself listens on port 80 as packaged.

Plan a supervised session of up to four hours and end it the same day with [explicit stop and withdrawal](../DAY-TWO-RUNBOOK.md#end-the-session). Basis for that bound: collection on this NQ package was observed continuously for four hours on one agent-driven guest; longer sessions are not covered. Separately, the one-use grant lifetime is two hours; grant expiry does not stop collection. This candidate's NQ has bounded retention (issue #27 remains open): the store still grows, at a planning figure of about 27 MB per hour on this trial, and by arithmetic from that figure reaches its 1 GiB per-file ceiling after roughly 40 hours, before anything is old enough to expire, so the seven-day retention target is never reached here. Behaviour at the ceiling is derived from code reading and component-level runs, not exercised on a guest of this package set: the collector is expected to refuse new collections and Workbench to show `stale` without naming the cause. No same-VM recovery is supplied. Nothing here claims unattended operation; see [known issues](../KNOWN-ISSUES.md).

The remediation consumer is installed disabled and this path does not enable it. Every Start here is one an operator requests step by step.

In the earlier recorded qualification, after a reboot systemd started nginx at boot outside governance, and Workbench reads `current` on the new
boot. The attempt line then includes `Prepared in an earlier boot (…); the host is now in boot …`, so the
completed attempt is not mistaken for the restart. The one-use grant stays spent.
