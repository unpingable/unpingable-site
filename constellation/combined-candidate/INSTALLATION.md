# Installation: choose one fresh VM path

This guide describes `constellation-canonical-candidate-20261010`, a prepared candidate that is not approved, not published and not distributed. The [nginx try path](try/README.md) is primary. Use only its assembled packages and the release record supplied with it. Do not substitute either earlier archive (8 October, retired; 10 October supervised, superseded), do not mix their packages with this candidate, and do not install these packages over the 8 October candidate ([known issues](KNOWN-ISSUES.md)). Qualification and release approval are separate from installation instructions.

Use a private, disposable **Ubuntu 22.04 amd64 VM** with systemd 249+, unified cgroup v2, Python 3.10, sudo/root and normal Ubuntu dependencies. On a qualification guest of this package set (an earlier assembly of this candidate with the same packages and scripts), the try path ran offline with supplied nginx packages on Ubuntu 22.04 with 4096 MB RAM, 2 CPUs and a 20 GiB disk. All such guests were agent-driven lab runs, not human evidence. Runs on the exact archive are recorded in `QUALIFICATION.json` beside the archive. Other sizes, the online apt path and Multipass are unexercised. No source checkout or compiler is needed. Do not install on a production or existing Constellation machine. Plan a supervised session of up to four hours and end it the same day; [capacity refusal and the other limits](KNOWN-ISSUES.md) remain explicit.

The default trial needs no ATProto account, model-provider account or production notification destination. Downloading Ubuntu dependencies/nginx requires network access unless their packages are supplied offline. A VM browser is optional: use the loopback SSH forward below from a browser on your own machine.

## Verify the exact artifact

No download is available: this candidate is not approved or distributed. If the release approver supplies the archive for a supervised session, obtain with it the release record beside the archive (`ARTIFACT.json` and the `.sha256` file), which carries its SHA256. The qualification guests of this package set were given only the archive and its `.sha256` file; `ARTIFACT.json` and `QUALIFICATION.json` did not exist beside it then. If they are not supplied with the archive you receive, ask the release approver before executing anything. A checksum from the same origin as the archive is not independent authentication. The names below identify this candidate; no archive checksum is embedded in these documents.

From the directory holding that archive:

```sh
sha256sum --check constellation-canonical-candidate-20261010.tar.gz.sha256
tar --extract --gzip --file constellation-canonical-candidate-20261010.tar.gz
cd constellation-canonical-candidate-20261010
```

The adjacent `QUALIFICATION.json` records the qualification of this exact archive; the bundled `QUALIFICATION-SUMMARY.json` states no result for it and only lists what is carried from predecessors by package byte identity, with the limits. `SOURCE-IDENTITIES.json`, `RUNTIME-IDENTITIES.json` and `PACKAGES.json` name the bundled sources/runtime/package bytes. These are different records, not interchangeable approvals.

## Primary nginx trial

Run the supplied script **instead of installing/enrolling the manual fixture below**. From the extracted directory above, with the verified archive still one directory above it:

```sh
sudo try/try-constellation.sh --archive ../constellation-canonical-candidate-20261010.tar.gz \
  --sha256 "$(cut -d' ' -f1 ../constellation-canonical-candidate-20261010.tar.gz.sha256)"
```

Initialization must use the same file limits and helper controls as the intended collector service; this candidate's enrollment path provides that boundary. Do not initialize separately with an unrestricted shell and later lower the service limit. The script checks the supplied hash and internal manifests, installs dependencies/nginx and eleven local packages, installs port 8081 confinement, enrolls `nginx.service`, and starts the collector, native reader and Workbench. Installation and enrollment are distinct steps even though this script performs both. It refuses existing enrollment. For offline nginx dependencies see [try/README.md](try/README.md); optional lab replacement flags are not newcomer steps.

The script extracts its working copy under `/opt/constellation-try/constellation-canonical-candidate-20261010`. **Run subsequent `scripts/native-action.py` commands from that working copy**, not from `try/`:

```sh
cd /opt/constellation-try/constellation-canonical-candidate-20261010
```

Open `http://127.0.0.1:18861/operator.html` in the VM browser; the plan is `/plan.html`. From your own machine, using your existing authorized guest account and SSH identity, forward only the local address:

```sh
ssh -N -L 127.0.0.1:18861:127.0.0.1:18861 USER@VM
```

Then open the same local Workbench URL. Replace `USER@VM` with the admitted guest login; this command neither creates an account nor grants SSH access. Do not forward port 8081 to other machines.

## Manual alternative and human study

This is a separate fresh VM path for the [prepared study](HUMAN-OPERABILITY.md), using `constellation-beta-http-fixture.service`, which runs harmless `sleep infinity` despite its historical name. Nobody supplies that unit beforehand: the enrollment helper below creates, enables and starts it, and its code refuses when the unit file already exists (that refusal was not exercised), so do not create the unit yourself. It has no HTTP watcher. Do not run `try/` on this VM before or after it.

From the verified extracted directory, install prerequisites online, or provide corresponding Ubuntu packages separately for offline use:

```sh
sudo apt-get update
sudo apt-get install python3 adduser systemd util-linux openssl libc6 libgcc-s1 sudo coreutils curl ca-certificates
sha256sum --check SHA256SUMS
sudo dpkg --install packages/*.deb
sudo dpkg --audit
sha256sum --check installed-SHA256SUMS
```

Before enrollment starts the reader, apply the same persistent port restriction used by `try/`. The drop-in directory must not already exist on this fresh VM:

```sh
sudo install -d -m 0755 /etc/systemd/system/constellation-live-reader.service.d
printf '[Service]\nIPAddressDeny=any\nIPAddressAllow=localhost\n' | sudo tee /etc/systemd/system/constellation-live-reader.service.d/loopback.conf >/dev/null
sudo chmod 0644 /etc/systemd/system/constellation-live-reader.service.d/loopback.conf
sudo systemctl daemon-reload
sudo python3 scripts/enroll-local-fixture.py --candidate "$PWD" --admit-disposable-unit-start
```

The helper explicitly enables and starts Workbench; there is no missing enable step. Verify the confinement before continuing:

```sh
systemctl show constellation-live-reader.service --property=DropInPaths,IPAddressDeny,IPAddressAllow
curl --fail --max-time 3 http://127.0.0.1:8081/api/read
```

Expect the exact `loopback.conf` path, deny `0.0.0.0/0 ::/0`, and allow `127.0.0.0/8 ::1/128`. These two commands show the configuration and that loopback answers. **They do not demonstrate the restriction.** A request to port 8081 on **each guest non-loopback address** must fail; the primary try script performs this check automatically, and the manual path does not. The check run on the manual-path qualification guest of this package set listed the addresses and requested the VM's own non-loopback IPv4 address (there `10.0.2.15`; use your VM's):

```sh
ip -brief addr
curl --fail --max-time 3 -sS -o /dev/null -w "http=%{http_code} local=%{local_ip} remote=%{remote_ip}\n" -g "http://10.0.2.15:8081/api/read"
```

Observed: `curl: (28) Connection timed out after 3000 milliseconds`, `http=000`, exit 28, with the listener on `0.0.0.0:8081`, while the `127.0.0.1` request above answered 200. What this shows: from inside the VM, a request to its own non-loopback IPv4 address gets no answer. What it does not show: it is a same-host probe, and reachability of port 8081 from another machine was not tested. The same request to the guest's IPv6 addresses was refused at once because the reader has no IPv6 listener; that says nothing about the filter. If the restriction is absent or any such read succeeds, stop and disable the reader with `sudo systemctl disable --now constellation-live-reader.service`; do not continue the manual trial. Preserve the partial enrollment and use [failure guidance](DAY-TWO-RUNBOOK.md#failed-or-interrupted-enrollment). Workbench itself listens only on loopback port 18861. The same SSH forward works for this path; retain this extracted directory as the native-action working directory.

## Local data and accounts

Enrollment creates local machine/boot/unit identities, observations and times, helper admissions, action preparations/results and worker identities. Configuration is under `/etc/nq`, `/etc/constellation-live-ecad` and `/etc/constellation-workbench`; observations are under `/var/lib/nq-ops`, and protected tokens/issuer material and attempt records are under `/var/lib/constellation-live-ecad`. Do not share private tokens or issuer keys with evidence captures. Review/redact records before sending them to another person; the default recipe supplies no automatic external evidence-sharing destination.

The native reader/action facade binds `0.0.0.0:8081`. Its GET reads have no credential; POST `/api/actions` uses the protected operator token. The confinement restricts access, it does not change the bind address or authenticate GET. nginx uses its packaged port 80 on the primary path. Package accounts/helper identities are installed automatically; the operator needs sudo for enrollment/actions. No claim of zero telemetry follows from this limited recipe description.

## Advanced reference

The bundled reference spine is a different installation path with its own historical qualification and limits. It and `scripts/enroll-canary-observation.sh` initialise NQ outside the bounded wrapper and have not been run with this NQ package: do not use them with this candidate ([known issues](KNOWN-ISSUES.md)), and do not combine them with this enrollment/store. Earlier install/day-two records do not qualify this candidate for unattended use. Optional remediation v2 needs separate inference budget/provider configuration and authorization; no such account is needed here.
