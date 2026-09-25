#!/usr/bin/env python3
"""Clean-install qualification of a reviewed-local-copy/v1 cohort release.

QUALIFICATION-ONLY HARNESS. Nothing here is part of the product path. It boots
one disposable Debian 12 guest from a verified read-only base image (qcow2
overlay, cloud-init seed, user networking with restrict=on and one SSH
hostfwd on 127.0.0.1, qemu -sandbox on), copies in only the release bundle
(cohort manifest, artifacts, SHA256SUMS, and the qualification-only fixture
tooling) and the harness's guest scripts, and runs the documented newcomer
steps with the driver extracted from the bundle's cohort-kit artifact:

    step 1 (published digests, no kit code) -> verify-manifest -> install
    -> init (fixture-review) -> fixture -> review -> status
    -> SYNTHETIC OPERATOR accept -> status -> evidence

plus refusal cases, each on its own cohort where it consumes an occurrence,
and the lane H hostile review's attacks against this bundle: altered kits
(F1), a pre-installed forged or edited nq-ng (F2) and an artifact swapped
between check and use (F3). The published digests are read from the kit
README's step 1, exactly as a newcomer copies them.
The acceptance step is performed by this harness as a labelled synthetic
operator (case W-03), never by the driver: the driver has no automatic
acceptance. The fixture-review route qualifies install, wiring, custody,
authority and effect; never review independence. The real provider route is
an operator-run qualification and is not exercised here.

Every case ends PASS, FAIL or NOT_EXERCISED with the observed output; nothing
is relabelled. A case that cannot run because an earlier case failed is
NOT_EXERCISED and names what blocked it. Modelled on NQ
qualification/release-closure-v1/run_acceptance.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import traceback
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
GUEST_SCRIPTS = ("probe.sh", "expire_issuance.py", "keyless_ag.py")
HARNESS_FILES = ("run_clean_install.py", "compose_bundle.py", *(f"guest/{name}" for name in GUEST_SCRIPTS))
# The evidence verifier ships in the cohort kit (setup/). The harness runs the
# bytes from the bundle's kit tarball, on the host and in the guest.
KIT_VERIFIER = "setup/verify_cohort_evidence.py"
# AG 58122ce enrollment identities (PKG-ag revision 2) and the superseded
# e20c23a ones, which must appear nowhere in the new cohort's evidence.
AG_ENROLLED = {"ag-loopctl": "af5fe488c0d9ec23fbbefbb5ef527ec05843ef433cbd484eb310fd8da50c323f",
               "ag-standing-resolver": "7a42b5ea16353ec918d57656f35a1f729f394f9c0b2cc82c17e24b21c453f68e"}
AG_SUPERSEDED = {"ag-loopctl": "1ea51d0499a81ee0303a55abf2ad3ef7cbcd10d67e398d64644aac86186a970a",
                 "ag-standing-resolver": "b96ad7b0bee2a654e35c6c0c4654921203d76e81767e5a1a402e56f8c6898ff2"}
IMAGE_NAME = "debian-12-genericcloud-amd64-20260903-2590.qcow2"
DEFAULT_IMAGE = pathlib.Path(
    "/data/git/.campaign-artifacts/constellation-operator-beta-composed-m2-run-002/input"
) / IMAGE_NAME
DEFAULT_OUTPUT_ROOT = pathlib.Path("/data/git/.campaign-artifacts/alpha-exit-closure-20260925/cohort-clean-install")
DEFAULT_STATE = pathlib.Path.home() / ".local/state/alpha-exit-cohort-clean-install"
GUEST_USER = "cohortqual"
GUEST_HOME = f"/home/{GUEST_USER}"
# README step 1: the kit is extracted as root, so nothing an unprivileged
# account can change runs as root.
KIT = "/opt/constellation/kit"
README = HERE.parents[1] / "examples" / "reviewed_local_copy" / "README.md"
HOSTILE_MARKERS = ("/tmp/hostile-kit-shadow-marker", "/tmp/hostile-kit-shadow-marker-f4")
BUNDLE = f"{GUEST_HOME}/bundle"
FIXTURE = f"{GUEST_HOME}/fixture"
EVIDENCE = "/root/cohort-evidence"
# Cohorts: A is the newcomer path; B the stale fixture review; C the expired issuance.
COHORTS = {"A": ("qual-a", 18431, "accepted"), "B": ("qual-b", 18432, "stale"), "C": ("qual-c", 18433, "accepted")}

CASES = (
    ("P-01", "preflight: tools, KVM, base image SHA-512, free port, bundle SHA256SUMS"),
    ("I-01", "boot a fresh Debian 12 guest; copy the bundle; README step 1: sha256sum --check of the manifest and "
             "kit against the published digests (no kit code); extract only the cohort kit as root"),
    ("I-02", "host facts the driver depends on (python3.11, openssl Ed25519, systemd-run, setpriv)"),
    ("I-03", "driver unit tests from the extracted kit under the guest's python3.11 -I -S"),
    ("N-01", "a manifest naming a wrong artifact digest refuses (verify-manifest and install), writing nothing"),
    ("N-02", "an artifact whose bytes differ from the manifest digest refuses, writing nothing"),
    ("N-03", "a manifest naming another source commit refuses (pin.incompatible)"),
    ("N-04", "install refuses as a non-root account"),
    ("H-01", "--help: no internal command or ==SUPPRESS== leaks; every option of every command has help"),
    ("K-02", "F1: altered kits (planted setup/json.py, zero commit, altered driver, and the hostile review's own "
             "k1-k3) fail the published-digest check; the genuine driver refuses each; the planted module never runs"),
    ("I-04", "verify-manifest and install: every pin, artifact digest and build info checked"),
    ("I-05", "init fixture-review: account, synthetic identities and keys, codex home, plan, ports, NQ watcher"),
    ("N-05", "re-running init on the existing cohort refuses and changes nothing"),
    ("T-01", "F3: a forged-build-info docket tarball is refused by digest; a tarball swapped back and forth during "
             "install never installs the forged bytes"),
    ("S-01", "status as a non-root account: host.not_root, exit 2, one JSON object (no traceback)"),
    ("F-01", "loopback fixture endpoint (qualification-only tooling) on guest 127.0.0.1"),
    ("W-01", "review: one durable unit, fresh observation, AG genesis, one bounded fixture review, stops before acceptance"),
    ("W-02", "status: retained candidate digest; zero grants, spends, attempts, effects; acceptance shows the "
             "text, destination, byte count, findings and time left"),
    ("W-03", "SYNTHETIC OPERATOR acceptance of the exact candidate digest (harness step, labelled)"),
    ("W-04", "status after execution: settled success, result.txt written once with the reviewed bytes"),
    ("S-03", "status counters after accept: current counts 1/1/1 and one result file; review-time counters labelled "
             "and still 0"),
    ("W-05", "evidence: bundle exported; driver join complete; the kit's verifier passes on the host; AG enrollment "
             "follows the repin"),
    ("V-01", "the in-kit verifier under guest python3.11 -I -S: passes the export, fails a byte-flipped copy"),
    ("K-01", "keyless AG inspect, replay, history and status over the settled cohort: identical without the issuer key; "
             "an absent enrolled file exits 3 and is never success"),
    ("N-06", "accept naming a digest other than the retained candidate refuses with no grant or effect"),
    ("N-07", "a second execute attempt refuses: driver accept, the kit continuation and AG re-run; one effect"),
    ("N-08", "stale fixture review (cohort B) is refused before any candidate; no authority, no effect"),
    ("N-09", "expired issuance (cohort C) is never presented: AG refuses dispatch; no Docket record, no effect"),
    ("S-04", "accept after the 5-minute review deadline (cohort C) refuses review.expired and records nothing"),
    ("Q-02", "F2: an edited installed nq-ng file refuses install (dpkg --verify output parsed); nothing written"),
    ("Q-01", "F2: a pre-installed forged nq-ng (consistent md5sums, dpkg --verify clean) refuses install; nothing "
             "written; the genuine package is restored"),
)


class Refusal(Exception):
    """A precondition or harness invariant that stops the case."""


class Blocked(Exception):
    """The case cannot run because an earlier case did not produce its input."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_digest(path: pathlib.Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, check: bool = True, timeout: float | None = 600,
        stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(command, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout, check=False)
    if check and completed.returncode != 0:
        raise Refusal(f"command failed ({completed.returncode}): {shlex.join(command)}\n"
                      f"{completed.stderr.decode(errors='replace')[-2000:]}")
    return completed


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


class Guest:
    def __init__(self, port: int, root: pathlib.Path, key: pathlib.Path) -> None:
        self.port, self.root, self.key = port, root, key
        self.name = "cohort-clean-install-a"
        self.process: subprocess.Popen[bytes] | None = None
        self.command: list[str] = []

    def options(self) -> list[str]:
        return ["-i", str(self.key), "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new",
                "-o", f"UserKnownHostsFile={self.root / 'known_hosts'}", "-o", "LogLevel=ERROR"]

    def ssh_base(self) -> list[str]:
        return ["ssh", *self.options(), "-p", str(self.port), "-o", "ConnectTimeout=5",
                "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4", f"{GUEST_USER}@127.0.0.1"]

    def scp_base(self) -> list[str]:
        return ["scp", "-q", *self.options(), "-P", str(self.port)]


class Harness:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.out: pathlib.Path = args.output_root / args.output_name
        self.state: pathlib.Path = args.state_dir
        self.started = utc_now()
        self.results = {cid: {"id": cid, "title": title, "outcome": "NOT_EXERCISED", "reason": "not reached"}
                        for cid, title in CASES}
        self.current: str | None = None
        self.case_started = 0.0
        self.guest: Guest | None = None
        self.identity: dict[str, Any] = {}
        self.facts: dict[str, Any] = {}
        self.host_log = None

    # ---------------------------------------------------------------- records
    def log(self, message: str) -> None:
        line = f"[{utc_now()}] {message}"
        print(line, flush=True)
        if self.host_log is not None:
            self.host_log.write(line + "\n")
            self.host_log.flush()

    def append_case(self, data: str) -> None:
        if self.current is not None:
            with (self.out / "cases" / f"{self.current}.log").open("a", encoding="utf-8") as handle:
                handle.write(data)

    def write_results(self) -> None:
        document = {
            "schema": "constellation.cohort-clean-install-result/v1",
            "campaign": "alpha-exit-closure-20260925",
            "profile": "reviewed-local-copy/v1",
            "review_route": "fixture-review",
            "review_route_claim": "install, wiring, custody, authority and effect; never review independence",
            "operator_acceptance": "synthetic operator performed by this harness (case W-03); not a human attestation",
            "harness": self.identity.get("harness"),
            "invocation": sys.argv,
            "started_at": self.started,
            "updated_at": utc_now(),
            "bundle": self.identity.get("bundle"),
            "base_image": self.identity.get("image"),
            "guest": {"name": self.guest.name, "ssh_port": self.guest.port, "qemu_command": self.guest.command}
            if self.guest else None,
            "guest_facts": self.identity.get("guest_facts"),
            "facts": self.facts,
            "summary": {o: sum(1 for r in self.results.values() if r["outcome"] == o)
                        for o in ("PASS", "FAIL", "NOT_EXERCISED")},
            "cases": [self.results[cid] for cid, _ in CASES],
        }
        tmp = self.out / "CLEAN-INSTALL-RESULT.json.tmp"
        tmp.write_text(json.dumps(document, indent=2, default=str) + "\n", encoding="utf-8")
        os.replace(tmp, self.out / "CLEAN-INSTALL-RESULT.json")

    def begin(self, cid: str) -> None:
        self.current = cid
        self.case_started = time.monotonic()
        self.log(f"== {cid} {dict(CASES)[cid]}")
        self.append_case(f"# {cid} {dict(CASES)[cid]}\n# started {utc_now()}\n")

    def record(self, outcome: str, **fields: Any) -> None:
        assert self.current is not None
        entry = self.results[self.current]
        entry.pop("reason", None)
        entry.update({"outcome": outcome, "recorded_at": utc_now(), "log": f"cases/{self.current}.log",
                      "elapsed_s": round(time.monotonic() - self.case_started, 1), **fields})
        self.append_case(f"# outcome {outcome} {json.dumps(fields, default=str)}\n")
        self.log(f"   -> {outcome}")
        self.current = None
        self.write_results()

    def run_case(self, cid: str, function, *args: Any) -> None:
        self.begin(cid)
        try:
            function(*args)
        except Blocked as error:
            self.record("NOT_EXERCISED", reason=f"blocked: {error}")
        except Refusal as error:
            self.record("FAIL", error=str(error), note="harness refusal during the case")
        except Exception as error:  # noqa: BLE001 - record, never hide
            self.append_case(traceback.format_exc())
            self.record("FAIL", error=f"{type(error).__name__}: {error}", note="unexpected exception")
        if self.current is not None:
            self.record("FAIL", error="case ended without recording an outcome")

    def passed(self, *cids: str) -> None:
        missing = [cid for cid in cids if self.results[cid]["outcome"] != "PASS"]
        if missing:
            raise Blocked(", ".join(f"{cid} is {self.results[cid]['outcome']}" for cid in missing))

    # --------------------------------------------------------------- guest io
    def ssh(self, command: str, *, check: bool = False, timeout: float = 900) -> subprocess.CompletedProcess[bytes]:
        assert self.guest is not None
        started = time.monotonic()
        try:
            done = run(self.guest.ssh_base() + [command], check=False, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            done = subprocess.CompletedProcess(error.cmd, 124, error.stdout or b"", (error.stderr or b"") + b"\n[timeout]")
        self.append_case(f"\n$ {command}\n# exit {done.returncode} in {time.monotonic() - started:.1f}s\n"
                         + (f"--- stdout\n{text(done.stdout)}\n" if done.stdout else "")
                         + (f"--- stderr\n{text(done.stderr)}\n" if done.stderr else ""))
        if check and done.returncode != 0:
            raise Refusal(f"exit {done.returncode}: {command}\n{text(done.stderr)[-1500:]}{text(done.stdout)[-1500:]}")
        return done

    def scp_to(self, sources: list[pathlib.Path], destination: str) -> None:
        assert self.guest is not None
        run(self.guest.scp_base() + [str(s) for s in sources] + [f"{GUEST_USER}@127.0.0.1:{destination}"])

    def driver(self, arguments: str, *, root: bool = True, timeout: float = 900) -> tuple[int, dict[str, Any]]:
        """The newcomer's command: python3.11 -I -S <kit>/setup/constellation_cohort.py ..."""
        started = time.monotonic()
        done = self.ssh(("sudo " if root else "") + f"{self.facts['driver']} {arguments}", timeout=timeout)
        try:
            value = json.loads(done.stdout)
        except ValueError:
            raise Refusal(f"driver output is not one JSON object: {text(done.stdout)[-500:]}") from None
        self.facts.setdefault("driver_calls", []).append(
            {"arguments": arguments.split(" --")[0], "exit": done.returncode, "elapsed_s": round(time.monotonic() - started, 2),
             "result": value.get("result"), "code": value.get("code")})
        return done.returncode, value

    def guest_json(self, command: str) -> Any:
        return json.loads(self.ssh(command, check=True).stdout)

    def writes_snapshot(self) -> str:
        return text(self.ssh("sudo find /opt/constellation /var/lib/constellation /etc/nq /var/lib/nq -maxdepth 3 "
                             "2>/dev/null | sort | sha256sum", check=True).stdout).split()[0]

    # --------------------------------------------------------------- preflight
    def describe_harness(self) -> dict[str, Any]:
        def git(*arguments: str) -> str | None:
            done = subprocess.run(["git", "-C", str(HERE), *arguments], capture_output=True, text=True, check=False)
            return done.stdout.strip() if done.returncode == 0 else None
        return {"directory": str(HERE), "commit": git("rev-parse", "HEAD"),
                "dirty_paths": (git("status", "--porcelain", "--", ".") or "").splitlines(),
                "files": {name: file_digest(HERE / name) for name in HARNESS_FILES}}

    def preflight(self) -> None:
        if (self.out / "CLEAN-INSTALL-RESULT.json").exists():
            raise Refusal(f"output already exists: {self.out}")
        for sub in ("cases", "evidence", "qemu"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        self.host_log = (self.out / "host.log").open("a", encoding="utf-8")
        self.identity["harness"] = self.describe_harness()
        self.run_case("P-01", self.case_p01)
        if self.results["P-01"]["outcome"] != "PASS":
            raise Refusal(self.results["P-01"].get("error", "preflight failed"))

    def case_p01(self) -> None:
        for tool in ("qemu-img", "qemu-system-x86_64", "xorriso", "ssh", "ssh-keygen", "scp"):
            if shutil.which(tool) is None:
                raise Refusal(f"required tool is absent: {tool}")
        if not os.access("/dev/kvm", os.R_OK | os.W_OK):
            raise Refusal("/dev/kvm is not accessible")
        if not port_free(self.args.ssh_port):
            raise Refusal(f"127.0.0.1:{self.args.ssh_port} is not free")
        if self.state.exists() and any(self.state.iterdir()):
            raise Refusal(f"state directory is not empty: {self.state}")
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        image = self.args.image
        expected = None
        for line in (image.parent / "SHA512SUMS").read_text().splitlines():
            digest, _, name = line.strip().partition("  ")
            if name == image.name:
                expected = digest
        actual = file_digest(image, "sha512")
        if expected is None or actual != expected:
            raise Refusal("base image is absent from SHA512SUMS or differs")
        if os.access(image, os.W_OK):
            raise Refusal("base image must not be writable")
        self.identity["image"] = {"path": str(image), "sha512": actual}
        bundle = self.args.bundle_dir
        checked = subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=bundle,
                                 capture_output=True, text=True, check=False)
        if checked.returncode != 0:
            raise Refusal(f"bundle SHA256SUMS do not verify on the host: {checked.stdout}{checked.stderr}")
        names = [line.split("  ", 1)[1] for line in (bundle / "SHA256SUMS").read_text().splitlines() if line]
        if "cohort-manifest.json" not in names:
            raise Refusal("bundle has no cohort-manifest.json listed in SHA256SUMS")
        manifest = json.loads((bundle / "cohort-manifest.json").read_text())
        self.identity["bundle"] = {"directory": str(bundle), "sha256sums_sha256": file_digest(bundle / "SHA256SUMS"),
                                   "manifest_sha256": "sha256:" + file_digest(bundle / "cohort-manifest.json"),
                                   "manifest": manifest, "files": names}
        self.identity["host_verifier"] = self.extract_host_verifier(bundle)
        published = self.published_digests()
        self.identity["published"] = published
        on_host = {name: "sha256:" + file_digest(bundle / name) for name in published["files"]}
        if on_host != published["files"]:
            raise Refusal(f"the bundle does not match the published digests: {on_host} != {published['files']}")
        self.record("PASS", image_sha512=actual, bundle=self.identity["bundle"], published=published)

    def published_digests(self) -> dict[str, Any]:
        """README step 1's heredoc: the published manifest and kit digests."""
        lines = README.read_text().splitlines()
        start = lines.index("sha256sum --check --strict <<'EOF'")
        values = {}
        for line in lines[start + 1:]:
            if line == "EOF":
                break
            digest, _, name = line.partition("  ")
            values[name] = "sha256:" + digest
        source = {"readme": str(README), "readme_sha256": "sha256:" + file_digest(README)}
        if self.args.published_manifest_sha256 or self.args.published_kit_sha256:
            # Trials only: the README is filled in after the kit is built.
            kit = [name for name in values if name.startswith("cohort-kit-")][0]
            values = {"cohort-manifest.json": self.args.published_manifest_sha256, kit: self.args.published_kit_sha256}
            source["override"] = "trial: published values given on the command line"
        if len(values) != 2 or not all(str(v).startswith("sha256:") and len(v) == 71 for v in values.values()):
            raise Refusal(f"README step 1 does not publish two sha256 values: {values}")
        return {"files": values, "source": source}

    def extract_host_verifier(self, bundle: pathlib.Path) -> dict[str, Any]:
        """Take the verifier from the bundle's kit tarball; its digest must be the kit's BUILD-INFO entry."""
        [kit] = [p for p in bundle.iterdir() if p.name.startswith("cohort-kit-") and p.name.endswith(".tar.gz")]
        top = kit.name.removesuffix(".tar.gz")
        with tarfile.open(kit, "r:gz") as tar:
            raw = tar.extractfile(f"{top}/{KIT_VERIFIER}").read()
            info = json.loads(tar.extractfile(f"{top}/BUILD-INFO.json").read())
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        if info["files"].get(KIT_VERIFIER) != digest:
            raise Refusal(f"the kit's {KIT_VERIFIER} does not match its BUILD-INFO.json")
        target = self.state / "host-kit" / KIT_VERIFIER
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        self.host_verifier = target
        return {"path": str(target), "sha256": digest, "kit": kit.name, "kit_commit": info["source_commit"]}

    def host_verify(self, directory: pathlib.Path) -> tuple[int, dict[str, Any], bytes]:
        done = run([sys.executable, "-I", "-S", "-B", str(self.host_verifier), "--evidence", str(directory)], check=False)
        try:
            value = json.loads(done.stdout)
        except ValueError:
            value = {"stderr": text(done.stderr)[-2000:]}
        return done.returncode, value, done.stdout

    # ------------------------------------------------------------------ guest
    def prepare_guest(self) -> Guest:
        root = self.state / "a"
        root.mkdir(mode=0o700)
        key = root / "id_ed25519"
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "cohort-clean-install", "-f", str(key)])
        guest = Guest(self.args.ssh_port, root, key)
        public_key = key.with_suffix(".pub").read_text().strip()
        (root / "meta-data").write_text(f"instance-id: {guest.name}\nlocal-hostname: {guest.name}\n")
        (root / "user-data").write_text(f"""#cloud-config
disable_root: true
hostname: {guest.name}
package_update: false
package_upgrade: false
preserve_hostname: false
ssh_pwauth: false
users:
  - name: {GUEST_USER}
    groups: [sudo]
    lock_passwd: true
    shell: /bin/bash
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    ssh_authorized_keys:
      - "{public_key}"
""")
        run(["xorriso", "-as", "mkisofs", "-quiet", "-output", str(root / "seed.iso"), "-volid", "cidata",
             "-joliet", "-rock", str(root / "user-data"), str(root / "meta-data")])
        # The genericcloud root is about 3 GB; grow the overlay for three cohorts.
        run(["qemu-img", "create", "-q", "-f", "qcow2", "-b", str(self.args.image), "-F", "qcow2",
             str(root / "overlay.qcow2"), "16G"])
        self.guest = guest
        return guest

    def start_guest(self, guest: Guest) -> None:
        root = guest.root
        guest.command = [
            "qemu-system-x86_64", "-name", f"{guest.name},process={guest.name}",
            "-no-user-config", "-nodefaults", "-accel", "kvm", "-machine", "q35", "-cpu", "host",
            "-smp", str(self.args.vcpus), "-m", str(self.args.memory_mib), "-display", "none", "-monitor", "none",
            "-serial", f"file:{root / 'serial.log'}", "-pidfile", str(root / "qemu.pid"),
            "-drive", f"if=virtio,file={root / 'overlay.qcow2'},format=qcow2,cache=none,aio=threads",
            "-drive", f"if=virtio,file={root / 'seed.iso'},format=raw,readonly=on",
            "-netdev", f"user,id=mgmt,restrict=on,hostfwd=tcp:127.0.0.1:{guest.port}-:22",
            "-device", "virtio-net-pci,netdev=mgmt,mac=52:54:00:9c:51:01",
            "-sandbox", "on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny",
        ]
        (self.out / "qemu" / "a-command.txt").write_text(shlex.join(guest.command) + "\n")
        guest.process = subprocess.Popen(guest.command, stdout=(root / "qemu.stdout.log").open("wb"),
                                         stderr=(root / "qemu.stderr.log").open("wb"), start_new_session=True)
        self.log(f"started {guest.name} pid {guest.process.pid} ssh 127.0.0.1:{guest.port}")

    def wait_ssh(self, guest: Guest, limit: int = 900) -> None:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            if guest.process is not None and guest.process.poll() is not None:
                raise Refusal(f"{guest.name} exited: {(guest.root / 'qemu.stderr.log').read_text()[-1000:]}")
            try:
                if run(guest.ssh_base() + ["true"], check=False, timeout=30).returncode == 0:
                    return
            except subprocess.TimeoutExpired:
                continue
            time.sleep(3)
        raise Refusal(f"{guest.name} SSH not reachable within {limit}s")

    def destroy(self) -> None:
        guest = self.guest
        if guest is None or guest.process is None or self.args.keep_guest:
            return
        if guest.process.poll() is None:
            guest.process.terminate()
            try:
                guest.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                guest.process.kill()
                guest.process.wait(timeout=30)
        if (guest.root / "serial.log").exists():
            shutil.copy2(guest.root / "serial.log", self.out / "evidence" / "a-serial.log")
        (guest.root / "overlay.qcow2").unlink(missing_ok=True)

    # ------------------------------------------------------------------ install
    def case_i01(self) -> None:
        guest = self.prepare_guest()
        self.start_guest(guest)
        self.wait_ssh(guest)
        self.ssh("cloud-init status --wait >/dev/null; cloud-init status", timeout=900)
        release = self.ssh('. /etc/os-release; printf "%s:%s" "$ID" "$VERSION_ID"', check=True).stdout
        if release != b"debian:12":
            raise Refusal(f"not Debian 12: {release!r}")
        self.ssh(f"mkdir -p {GUEST_HOME}/bin {BUNDLE}/qualification-only {FIXTURE}", check=True)
        self.scp_to([HERE / "guest" / name for name in GUEST_SCRIPTS], f"{GUEST_HOME}/bin/")
        bundle = self.args.bundle_dir
        self.scp_to(sorted(p for p in bundle.iterdir() if p.is_file()), f"{BUNDLE}/")
        self.scp_to(sorted((bundle / "qualification-only").iterdir()), f"{BUNDLE}/qualification-only/")
        # Newcomer step 1: the published digests, with sha256sum alone; then
        # the bundle's own SHA256SUMS; then extract only the cohort kit as root.
        anchored = self.anchored_check(BUNDLE)
        if anchored.returncode != 0:
            raise Refusal(f"README step 1 failed on the genuine bundle: {text(anchored.stdout)}{text(anchored.stderr)}")
        self.ssh(f"cd {BUNDLE} && sha256sum --check --strict SHA256SUMS", check=True)
        kit = [p.name for p in bundle.iterdir() if p.name.startswith("cohort-kit-") and p.name.endswith(".tar.gz")]
        if len(kit) != 1:
            raise Refusal("bundle must hold exactly one cohort-kit tarball")
        self.ssh(f"sudo mkdir -p -m 0755 {KIT} && sudo tar -xzf {BUNDLE}/{kit[0]} -C {KIT} --no-same-owner", check=True)
        top = kit[0].removesuffix(".tar.gz")
        self.facts["kit_root"] = f"{KIT}/{top}"
        self.facts["driver"] = f"/usr/bin/python3.11 -I -S {KIT}/{top}/setup/constellation_cohort.py"
        version = self.ssh(f"{self.facts['driver']} --version", check=True).stdout.strip()
        fixture = sorted((bundle / "qualification-only").iterdir())[0].name
        self.ssh(f"tar -xzf {BUNDLE}/qualification-only/{fixture} -C {FIXTURE} --no-same-owner", check=True)
        self.ssh(f"chmod 0755 {GUEST_HOME}/bin/*", check=True)
        self.record("PASS", os=release.decode(), driver_version=text(version), kit=kit[0],
                    published_check=text(anchored.stdout).strip().splitlines(), kit_root=self.facts["kit_root"],
                    fixture_tooling=fixture, note="fixture tooling is a qualification-only dependency")

    def anchored_check(self, directory: str) -> subprocess.CompletedProcess[bytes]:
        """README step 1 verbatim: sha256sum against the published values."""
        lines = "".join(f"{value.removeprefix('sha256:')}  {name}\n"
                        for name, value in self.identity["published"]["files"].items())
        return self.ssh(f"cd {directory} && sha256sum --check --strict <<'EOF'\n{lines}EOF")

    def case_i02(self) -> None:
        done = self.ssh(f"{GUEST_HOME}/bin/probe.sh", check=True)
        facts = json.loads(done.stdout)
        self.identity["guest_facts"] = facts
        (self.out / "evidence" / "guest-facts.json").write_bytes(done.stdout)
        missing = [name for name, ok in (
            ("debian:12", facts["os"] == "debian:12"),
            ("python3 is 3.11", facts["python3"].startswith("3.11.")),
            ("python3.11 present", facts["python311_sha256"] is not None),
            ("openssl Ed25519", facts["openssl_ed25519"]),
            ("systemd-run", facts["tools"]["systemd-run"]),
            ("setpriv", facts["tools"]["setpriv"]),
            ("memfd_create", facts["memfd_create"]),
        ) if not ok]
        self.record("FAIL" if missing else "PASS", missing=missing, facts=facts)

    def case_i03(self) -> None:
        summaries, ok = {}, True
        for name in ("test_constellation_cohort.py", "test_verify_cohort_evidence.py"):
            done = self.ssh(f"/usr/bin/python3.11 -I -S -B {self.facts['kit_root']}/setup/{name} -v 2>&1")
            tail = text(done.stdout).strip().splitlines()[-3:]
            summaries[name] = tail
            ok &= done.returncode == 0 and any(line.startswith("OK") for line in tail) \
                and not any("skipped" in line for line in tail)
        self.record("PASS" if ok else "FAIL", summary=summaries)

    # -------------------------------------------------------- manifest refusals
    def variant_manifest(self, name: str, component: str, field: str, value: str) -> str:
        path = f"{GUEST_HOME}/{name}.json"
        code = ("import json,sys; m=json.load(open(sys.argv[1])); "
                "[e.update({sys.argv[3]: sys.argv[4]}) for e in m['components'] if e['component']==sys.argv[2]]; "
                "open(sys.argv[5],'w').write(json.dumps(m))")
        self.ssh(f"/usr/bin/python3.11 -I -S -c {shlex.quote(code)} {BUNDLE}/cohort-manifest.json {component} "
                 f"{field} {shlex.quote(value)} {path}", check=True)
        return path

    def refuses_without_writes(self, manifest: str, artifacts: str, expected: str, fragment: str,
                               cohort: str = "qual-refused", verify: bool = True) -> dict:
        """verify-manifest (no root, as README step 2) and install (root) both refuse, writing nothing."""
        before = self.writes_snapshot()
        if verify:
            status_v, verified = self.driver(f"verify-manifest --manifest {manifest} --artifacts {artifacts}", root=False)
        else:
            status_v, verified = 2, {"code": expected, "detail": fragment, "note": "not run: install-only refusal"}
        status_i, install = self.driver(f"install --cohort {cohort} --manifest {manifest} --artifacts {artifacts}")
        after = self.writes_snapshot()
        ok = (status_v == 2 and verified.get("code") == expected and fragment in verified.get("detail", "")
              and status_i == 2 and install.get("code") == expected and fragment in install.get("detail", "")
              and before == after)
        return {"ok": ok, "verify": verified, "install": install, "writes_unchanged": before == after}

    def case_n01(self) -> None:
        wrong = "sha256:" + hashlib.sha256(b"some other docket build").hexdigest()
        manifest = self.variant_manifest("n01-manifest", "docket", "artifact_sha256", wrong)
        result = self.refuses_without_writes(manifest, BUNDLE, "pin.incompatible", "docket.artifact_sha256")
        self.record("PASS" if result.pop("ok") else "FAIL", **result)

    def case_n02(self) -> None:
        # Same manifest, one artifact's bytes changed: no file carries the digest.
        self.ssh(f"mkdir -p {GUEST_HOME}/n02 && cp {BUNDLE}/*.deb {BUNDLE}/*.tar.gz {GUEST_HOME}/n02/ && "
                 f"printf x >> {GUEST_HOME}/n02/docket-0.1.0-linux-amd64.tar.gz", check=True)
        result = self.refuses_without_writes(f"{BUNDLE}/cohort-manifest.json", f"{GUEST_HOME}/n02",
                                             "artifact.missing", "docket")
        self.ssh(f"rm -rf {GUEST_HOME}/n02", check=True)
        self.record("PASS" if result.pop("ok") else "FAIL", **result)

    def case_n03(self) -> None:
        # A descendant or other commit is a different pin (no ranges).
        manifest = self.variant_manifest("n03-manifest", "maude", "source_commit",
                                         "c1fce17a529c4f73d23012b22b7f1a2a3ee666a7")
        result = self.refuses_without_writes(manifest, BUNDLE, "pin.incompatible", "maude.source_commit")
        self.record("PASS" if result.pop("ok") else "FAIL", **result)

    def case_n04(self) -> None:
        status, result = self.driver(f"install --cohort qual-a --manifest {BUNDLE}/cohort-manifest.json "
                                     f"--artifacts {BUNDLE}", root=False)
        ok = status == 2 and result.get("code") == "host.not_root"
        self.record("PASS" if ok else "FAIL", result=result)

    # ---------------------------------------------------------------- newcomer
    def case_i04(self) -> None:
        status_v, verify = self.driver(f"verify-manifest --manifest {BUNDLE}/cohort-manifest.json --artifacts {BUNDLE}")
        installs = {}
        for label, (cohort, _, _) in COHORTS.items():
            installs[cohort] = self.driver(f"install --cohort {cohort} --manifest {BUNDLE}/cohort-manifest.json "
                                           f"--artifacts {BUNDLE}", timeout=900)
        identities = self.guest_json(f"sudo cat /opt/constellation/cohorts/qual-a/installed.json")
        # An identity's "component" is the executable's own name; select AG by its install root.
        ag = {pathlib.PurePosixPath(path).name: v["sha256"] for path, v in identities.get("identities", {}).items()
              if "/cohorts/qual-a/ag/" in path}
        ok = (status_v == 0 and verify.get("qualified_cohort") == "alpha-exit-rc"
              and all(ag.get(name, "").removeprefix("sha256:") == digest for name, digest in AG_ENROLLED.items())
              and all(status == 0 and value.get("result") == "installed" for status, value in installs.values()))
        self.record("PASS" if ok else "FAIL", verify=verify, install={k: v[1] for k, v in installs.items()},
                    executables={path: {k: v[k] for k in ("component", "sha256", "version", "source_commit")}
                                 for path, v in identities.get("identities", {}).items()})

    def init(self, cohort: str, port: int) -> tuple[int, dict]:
        return self.driver(f"init --cohort {cohort} --review-route fixture-review --fixture-port {port}")

    def case_i05(self) -> None:
        self.passed("I-04")
        inits = {cohort: self.init(cohort, port) for cohort, port, _ in COHORTS.values()}
        ok = all(status == 0 and value.get("result") == "initialized" for status, value in inits.values())
        self.facts["bindings"] = {cohort: value.get("binding_id") for cohort, (_, value) in inits.items()}
        self.record("PASS" if ok else "FAIL", init={k: v[1] for k, v in inits.items()})

    def case_n05(self) -> None:
        self.passed("I-05")
        cohort, port, _ = COHORTS["A"]
        before = text(self.ssh(f"sudo find /var/lib/constellation/cohorts/{cohort} /etc/nq -printf '%p %s %T@\\n' | "
                               "sort | sha256sum", check=True).stdout)
        status, result = self.init(cohort, port)
        after = text(self.ssh(f"sudo find /var/lib/constellation/cohorts/{cohort} /etc/nq -printf '%p %s %T@\\n' | "
                              "sort | sha256sum", check=True).stdout)
        ok = status == 2 and result.get("code") == "cohort.exists" and before == after
        self.record("PASS" if ok else "FAIL", result=result, state_unchanged=before == after)

    def start_fixture(self, label: str) -> dict:
        cohort, port, mode = COHORTS[label]
        extra = ""
        if mode == "stale":
            stale = self.facts.get("bindings", {}).get(COHORTS["A"][0])
            extra = f" --stale-binding-id {stale}"
        self.ssh(f"cd {FIXTURE} && (setsid nohup /usr/bin/python3.11 -I {FIXTURE}/fixture-review-tooling/"
                 f"fixture_responses_endpoint.py --port {port} --mode {mode}{extra} --log {FIXTURE}/{cohort}-requests.jsonl "
                 f"--ready-file {FIXTURE}/{cohort}-ready.json > {FIXTURE}/{cohort}.out 2>&1 &); "
                 f"for i in $(seq 50); do [ -s {FIXTURE}/{cohort}-ready.json ] && break; sleep 0.1; done", check=True)
        return self.guest_json(f"cat {FIXTURE}/{cohort}-ready.json")

    def fixture_requests(self, cohort: str) -> list:
        done = self.ssh(f"cat {FIXTURE}/{cohort}-requests.jsonl 2>/dev/null || true", check=True)
        return [json.loads(line) for line in text(done.stdout).splitlines() if line.strip()]

    def case_f01(self) -> None:
        self.passed("I-05")
        ready = {label: self.start_fixture(label) for label in COHORTS}
        listening = text(self.ssh("ss -Htln", check=True).stdout)
        ok = all(value["bind"] == "127.0.0.1" and f"127.0.0.1:{value['port']}" in listening for value in ready.values())
        exposed = [line for line in listening.splitlines() if any(f":{port} " in line + " " for _, port, _ in COHORTS.values())
                   and "127.0.0.1" not in line]
        self.record("PASS" if ok and not exposed else "FAIL", ready=ready, non_loopback=exposed,
                    note="qualification-only tooling; the product has no fixture")

    def review(self, label: str) -> tuple[int, dict]:
        cohort = COHORTS[label][0]
        return self.driver(f"review --cohort {cohort}", timeout=900)

    def unit_records(self, cohort: str, step: str) -> str:
        return text(self.ssh(f"sudo sh -c 'ls -d /var/lib/constellation/cohorts/{cohort}/driver/*-{step}/*-unit'",
                             check=True).stdout).strip()

    def optional_json(self, path: str) -> Any:
        done = self.ssh(f"sudo cat {path}")
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else None

    def review_facts(self, cohort: str, label: str) -> dict:
        """Timings and caller terminal of one review, whether it passed or refused."""
        unit = self.unit_records(cohort, "review")
        timings = self.optional_json(f"{unit}/review-timings.json")
        (self.out / "evidence" / f"{cohort}-review-timings.json").write_text(json.dumps(timings, indent=1) + "\n")
        terminal = self.optional_json(f"/var/lib/constellation/cohorts/{cohort}/review/review-001/terminal.json")
        unit_result = self.optional_json(f"{unit.rsplit('/', 1)[0]}/unit-result.json")
        return {"timings": timings, "caller_terminal": terminal, "unit_result": unit_result,
                "fixture_requests": len([r for r in self.fixture_requests(cohort)
                                         if r.get("kind") in ("responses_ws", "responses_sse")])}

    def case_w01(self) -> None:
        self.passed("I-05", "F-01")
        status, result = self.review("A")
        cohort = COHORTS["A"][0]
        facts = self.review_facts(cohort, "A")
        self.facts["review_timings"] = facts["timings"]
        ok = (status == 0 and result.get("result") == "reviewed" and result.get("verdict_accepted") is True
              and result.get("provider_calls") == 1 and result.get("grants") == 0 and result.get("effects") == 0)
        self.facts["candidate_sha256"] = result.get("candidate_sha256")
        self.facts["review_acceptance"] = result.get("acceptance")
        acceptance = result.get("acceptance") or {}
        ok = ok and acceptance.get("candidate_sha256") == result.get("candidate_sha256") \
            and acceptance.get("deadline", {}).get("expired") is False
        requests = self.fixture_requests(cohort)
        facts["fixture_turns"] = {"warmup_generate_false": sum(1 for r in requests if r.get("warmup") is True),
                                  "generating": sum(1 for r in requests if r.get("kind") in ("responses_ws", "responses_sse")
                                                    and not r.get("warmup")),
                                  "note": "the App Server's session-start prewarm (generate:false) precedes the one "
                                          "review request; see the kit README, Provider requests"}
        self.facts["fixture_turns"] = facts["fixture_turns"]
        self.record("PASS" if ok else "FAIL", result=result, **facts)

    def status(self, cohort: str) -> dict:
        status, value = self.driver(f"status --cohort {cohort}")
        if status != 0:
            raise Refusal(f"status refused: {value}")
        value.pop("identities", None)
        return value

    def case_w02(self) -> None:
        self.passed("W-01")
        value = self.status(COHORTS["A"][0])
        review = value.get("review", {})
        at_review = review.get("counters_at_review", {})
        acceptance = value.get("acceptance", {})
        will, deadline = acceptance.get("will_write", {}), acceptance.get("deadline", {})
        cohort = COHORTS["A"][0]
        expected_text = f"Constellation cohort {cohort} reviewed copy.\n"
        readable = (will.get("path") == f"/var/lib/constellation/cohorts/{cohort}/scratch/result.txt"
                    and will.get("text") == expected_text and will.get("bytes") == len(expected_text.encode())
                    and will.get("bound_by_plan") is True and acceptance.get("review", {}).get("findings")
                    and acceptance.get("candidate_sha256") == self.facts["candidate_sha256"]
                    and deadline.get("expired") is False and 0 < deadline.get("seconds_remaining", 0) <= 300
                    and self.facts["candidate_sha256"] in acceptance.get("accept_command", ""))
        ok = (review.get("candidate_sha256") == self.facts["candidate_sha256"]
              and set(at_review) == {"grants", "spends", "docket_attempts", "executor_calls", "effects"}
              and all(value == 0 for value in at_review.values())
              and value["native"].get("program_counter") == "proposal_recorded"
              and value["result_file"].get("present") is False and readable)
        self.record("PASS" if ok else "FAIL", readable_acceptance=bool(readable), acceptance=acceptance,
                    review_output_acceptance=self.facts.get("review_acceptance"), status=value)

    def case_w03(self) -> None:
        self.passed("W-02")
        # SYNTHETIC OPERATOR: the harness reads the candidate digest printed by
        # status and names it. Not a human attestation.
        candidate = self.status(COHORTS["A"][0])["review"]["candidate_sha256"]
        status, result = self.driver(f"accept --cohort {COHORTS['A'][0]} --candidate-sha256 {candidate}", timeout=900)
        ok = (status == 0 and result.get("result") == "accepted_and_executed" and result.get("human_attestation") is False
              and result.get("provider_calls_in_continuation") == 0)
        self.record("PASS" if ok else "FAIL", operator="SYNTHETIC OPERATOR (harness)", candidate_sha256=candidate,
                    result=result)

    def case_w04(self) -> None:
        self.passed("W-03")
        value = self.status(COHORTS["A"][0])
        native, result = value["native"], value["result_file"]
        self.facts["result_file_after_accept"] = {k: result.get(k) for k in ("sha256", "bytes", "scratch_entries")}
        self.facts["result_file_stat_after_accept"] = text(self.ssh(
            f"sudo stat -c '%i %s %Y %a %U' {result['path']}", check=True).stdout).strip()
        ok = (native.get("program_counter") == "settled_observation_required" and native.get("settlement_outcome") == "success"
              and native.get("replay", {}).get("ag_spends") == 1 and native.get("replay", {}).get("docket_attempts") == 1
              and native.get("replay", {}).get("settlements") == 1 and result.get("matches_plan") is True
              and result.get("scratch_entries") == ["result.txt"])
        self.record("PASS" if ok else "FAIL", native={k: v for k, v in native.items() if k != "docket_inspect"},
                    result_file=result)

    def case_w05(self) -> None:
        self.passed("W-04")
        status, result = self.driver(f"evidence --cohort {COHORTS['A'][0]} --output {EVIDENCE}")
        if status != 0:
            raise Refusal(f"evidence refused: {result}")
        archive = self.ssh(f"sudo tar -C {EVIDENCE} -czf - .", check=True).stdout
        target = self.out / "evidence" / "qual-a-evidence"
        target.mkdir()
        with tarfile.open(fileobj=__import__("io").BytesIO(archive), mode="r:gz") as tar:
            tar.extractall(target, filter="data")
        code, verified, raw = self.host_verify(target)
        (self.out / "evidence" / "qual-a-verifier.json").write_bytes(raw)
        enrollment = self.ag_enrollment(target)
        self.facts["ag_enrollment"] = enrollment
        ok = status == 0 and result.get("join_complete") is True and code == 0 \
            and verified.get("result") == "passed" and enrollment["follows_repin"]
        self.record("PASS" if ok else "FAIL", evidence=result, verifier=verified,
                    verifier_source=self.identity.get("host_verifier"), ag_enrollment=enrollment)

    @staticmethod
    def ag_enrollment(root: pathlib.Path) -> dict[str, Any]:
        """Where the new AG executables are enrolled, and that the superseded ones appear nowhere."""
        found: dict[str, list[str]] = {f"new:{k}": [] for k in AG_ENROLLED} | {f"old:{k}": [] for k in AG_SUPERSEDED}
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix == ".json"):
            data = path.read_bytes()
            for label, table in (("new", AG_ENROLLED), ("old", AG_SUPERSEDED)):
                for name, digest in table.items():
                    if digest.encode() in data:
                        found[f"{label}:{name}"].append(str(path.relative_to(root)))
        required = {"new:ag-loopctl": {"state/owner/nightshift-ag-cycle-config.json", "state/deployment/caller.json"},
                    "new:ag-standing-resolver": {"state/ports/ag-standing-enrollment.json",
                                                 "state/ports/ag-standing-manifest.json"}}
        follows = (all(need <= set(found[key]) for key, need in required.items())
                   and not any(found[f"old:{name}"] for name in AG_SUPERSEDED))
        return {"follows_repin": follows, "files": found}

    def case_v01(self) -> None:
        self.passed("W-05")
        verifier = f"{self.facts['kit_root']}/{KIT_VERIFIER}"
        digest = text(self.ssh(f"sha256sum {verifier}", check=True).stdout).split()[0]
        genuine = self.ssh(f"sudo /usr/bin/python3.11 -I -S {verifier} --evidence {EVIDENCE}")
        flipped_dir = "/root/cohort-evidence-v01-flipped"
        self.ssh(f"sudo sh -c 'cp -a {EVIDENCE} {flipped_dir} && chmod u+w {flipped_dir}/native/docket-inspect.json && "
                 f"printf \" \" >> {flipped_dir}/native/docket-inspect.json'", check=True)
        flipped = self.ssh(f"sudo /usr/bin/python3.11 -I -S {verifier} --evidence {flipped_dir}")
        self.ssh(f"sudo rm -rf {flipped_dir}", check=True)
        (self.out / "evidence" / "qual-a-verifier-in-guest.json").write_bytes(genuine.stdout)
        try:
            good, bad = json.loads(genuine.stdout), json.loads(flipped.stdout)
        except ValueError:
            raise Refusal(f"verifier output is not JSON: {text(genuine.stdout)[-300:]} {text(flipped.stdout)[-300:]}")
        host = json.loads((self.out / "evidence" / "qual-a-verifier.json").read_text())
        ok = (genuine.returncode == 0 and good.get("result") == "passed" and good.get("mismatched_plan_digest") == "refused"
              and all(good.get("checks", {}).values()) and good == host
              and "sha256:" + digest == self.identity["host_verifier"]["sha256"]
              and flipped.returncode == 1 and bad.get("result") == "failed"
              and bad.get("digest_mismatches") == ["native/docket-inspect.json"])
        self.record("PASS" if ok else "FAIL", verifier=verifier, verifier_sha256="sha256:" + digest,
                    interpreter="/usr/bin/python3.11 -I -S", genuine=good, equals_host_output=good == host,
                    flipped={"exit": flipped.returncode, "result": bad.get("result"),
                             "digest_mismatches": bad.get("digest_mismatches")})

    def case_k01(self) -> None:
        self.passed("W-04")
        cohort = COHORTS["A"][0]
        ag = f"/opt/constellation/cohorts/{cohort}/ag/ag-0.1.0/bin/ag-loopctl"
        done = self.ssh(f"sudo /usr/bin/python3.11 -I -S {GUEST_HOME}/bin/keyless_ag.py --kit-setup "
                        f"{self.facts['kit_root']}/setup --cohort {cohort} --ag {ag}", timeout=600)
        if done.returncode != 0:
            raise Refusal(f"keyless helper failed: {text(done.stderr)[-1500:]}")
        report = json.loads(done.stdout)
        (self.out / "evidence" / "qual-a-keyless-ag.json").write_bytes(done.stdout)
        variants = report["variants"]
        control = variants["with-key"]["commands"]
        live = self.status(cohort)["native"]
        verified = all(c["outcome"] == "verified" and c["exit"] == 0 for c in control.values())
        same = {name: all(variants[name]["commands"][cmd]["outcome"] == "verified"
                          and variants[name]["commands"][cmd]["stdout_sha256"] == control[cmd]["stdout_sha256"]
                          for cmd in control) for name in ("without-key", "garbage-key")}
        absent = variants["without-validator-config"]["commands"]
        exit3 = all(c["exit"] == 3 and c["outcome"] == "verified_except_unavailable"
                    and [u["role"] for u in c["unavailable"]] == ["shared_admission.plan_validator_config"]
                    for c in absent.values())
        ok = (verified and all(same.values()) and exit3 and report["ag_sha256"] == "sha256:" + AG_ENROLLED["ag-loopctl"]
              and control["inspect"]["program_counter"] == "settled_observation_required"
              and absent["inspect"]["state_digest"] == control["inspect"]["state_digest"]
              and not variants["without-key"]["key_present_in_view"] and report["live_key_present"])
        read_only = variants["read-only-database"]["commands"]["inspect"]
        self.record("PASS" if ok else "FAIL", ag_sha256=report["ag_sha256"],
                    state_digest=control["inspect"]["state_digest"], live_status_counter=live.get("program_counter"),
                    control_verified=verified, identical_without_key=same, absent_enrolled_file_exit3=exit3,
                    absent_report=absent["inspect"]["unavailable"], driver_classification=absent["inspect"]["outcome"],
                    read_only_database_probe={k: read_only[k] for k in ("exit", "outcome", "stderr_tail")},
                    note="read-only-database is an observation of the AG owner limitation (G3 X-04), not a gate")

    # ------------------------------------------------------------ workflow refusals
    def case_n06(self) -> None:
        self.passed("W-02")
        wrong = "sha256:" + hashlib.sha256(b"not the retained candidate").hexdigest()
        cohort = COHORTS["A"][0]
        status, result = self.driver(f"accept --cohort {cohort} --candidate-sha256 {wrong}")
        claimed = self.ssh(f"sudo test -e /var/lib/constellation/cohorts/{cohort}/driver/accept.claimed.json").returncode == 0
        grants = self.ssh(f"sudo test -e /var/lib/constellation/cohorts/{cohort}/ports/ag-mandates.json").returncode == 0
        ok = status == 2 and result.get("code") == "accept.candidate_mismatch" and not claimed and not grants
        self.record("PASS" if ok else "FAIL", result=result, accept_claimed=claimed, mandate_written=grants,
                    note="run before W-03 so the retained candidate stays unaccepted")

    def case_n07(self) -> None:
        self.passed("W-04")
        cohort = COHORTS["A"][0]
        candidate = self.facts["candidate_sha256"]
        state = f"/var/lib/constellation/cohorts/{cohort}"
        status, driver = self.driver(f"accept --cohort {cohort} --candidate-sha256 {candidate}")
        # The kit continuation directly, as the cohort account in a durable unit.
        kit = self.guest_json(f"sudo cat /opt/constellation/cohorts/{cohort}/installed.json")["roots"]["cohort-kit"]
        code = (f"import sys; sys.path.extend([{kit + '/setup'!r}, {kit!r}]); import continue_reviewed_action as c; "
                f"c.main(sys.argv[1:])")
        continued = self.ssh(
            f"sudo systemd-run --wait --pipe --collect --quiet --uid=constellation --gid=constellation "
            f"--setenv=PATH=/usr/bin:/bin --setenv=LANG=C.UTF-8 -- /usr/bin/python3.11 -I -S -c {shlex.quote(code)} "
            f"--config {state}/deployment/caller.json --retained-review {state}/review/review-001 "
            f"--accept-candidate-sha256 {candidate} --output {state}/runs/continuation-002 --accept-and-execute", timeout=300)
        rerun = self.ssh(f"sudo setpriv --reuid=constellation --regid=constellation --init-groups "
                         f"/opt/constellation/cohorts/{cohort}/ag/ag-0.1.0/bin/ag-loopctl run --database "
                         f"{state}/deployment/ag.sqlite --run-input {state}/runs/continuation-001/run-input-v2.json", timeout=120)
        value = self.status(cohort)
        stat_after = text(self.ssh(f"sudo stat -c '%i %s %Y %a %U' {value['result_file']['path']}", check=True).stdout).strip()
        replay = value["native"].get("replay", {})
        ok = (status == 2 and driver.get("code") == "accept.exists" and continued.returncode != 0
              and replay.get("ag_spends") == 1 and replay.get("docket_attempts") == 1 and replay.get("settlements") == 1
              and stat_after == self.facts.get("result_file_stat_after_accept")
              and value["result_file"].get("scratch_entries") == ["result.txt"])
        self.record("PASS" if ok else "FAIL", driver_accept=driver, continuation_exit=continued.returncode,
                    continuation_stderr=text(continued.stderr)[-800:], ag_rerun_exit=rerun.returncode,
                    ag_rerun=text(rerun.stdout)[-800:], replay=replay, result_stat_before=self.facts.get(
                        "result_file_stat_after_accept"), result_stat_after=stat_after)

    def case_n08(self) -> None:
        self.passed("I-05", "F-01")
        cohort = COHORTS["B"][0]
        status, result = self.review("B")
        facts = self.review_facts(cohort, "B")
        value = self.status(cohort)
        phase = (facts["caller_terminal"] or {}).get("phase")
        observed = {"result": result, **facts, "native": value.get("native")}
        if facts["fixture_requests"] == 0:
            self.append_case("\n# observed " + json.dumps(observed, default=str) + "\n")
            raise Blocked(f"the review refused before the fixture answered ({result.get('code')}: "
                          f"{result.get('detail', '')[:400]}), so staleness was not exercised")
        # The stale result may be refused by the caller's matching contract
        # check (prepare_review_candidate.project, which runs before the native
        # verifier) or by the native verifier itself. Record which.
        reason = (facts["caller_terminal"] or {}).get("reason", "")
        layer = ("native-review-verifier" if phase == "native-review-verification" else
                 "caller-contract-check" if reason == "review result does not match the native verifier contract" else None)
        answered = [r.get("binding_id") for r in self.fixture_requests(cohort) if r.get("mode") == "stale"]
        candidate = self.ssh(f"sudo test -e /var/lib/constellation/cohorts/{cohort}/review/review-001/"
                             "record-review-input.json").returncode == 0
        ok = (status == 2 and result.get("code") == "review.refused" and layer is not None and not candidate
              and value["native"].get("program_counter") == "proposal_recorded"
              and value["native"].get("replay", {}).get("ag_spends") == 0 and value["result_file"].get("present") is False)
        self.record("PASS" if ok else "FAIL", refusing_layer=layer, candidate_written=candidate,
                    fixture_stale_answers=len(answered), **observed)

    def case_n09(self) -> None:
        self.passed("I-05", "F-01")
        cohort = COHORTS["C"][0]
        status, result = self.review("C")
        if status != 0:
            raise Blocked(f"cohort C review refused ({result.get('code')}: {result.get('detail', '')[:300]}); "
                          "no candidate to accept")
        candidate = result["candidate_sha256"]
        self.facts["candidate_c"] = candidate
        done = self.ssh(f"sudo /usr/bin/python3.11 -I -S {GUEST_HOME}/bin/expire_issuance.py --cohort {cohort} "
                        f"--candidate-sha256 {candidate}", timeout=600)
        report = json.loads(done.stdout) if done.returncode == 0 else {"stderr": text(done.stderr)[-2000:]}
        value = self.status(cohort)
        replay = value["native"].get("replay", {})
        ok = (done.returncode == 0 and report.get("first_run", {}).get("reason") == "step_bound_exhausted"
              and report.get("second_run_refused") is True and replay.get("ag_spends") == 1
              and replay.get("docket_attempts") == 0 and report.get("docket_records") == 0
              and value["result_file"].get("present") is False)
        self.record("PASS" if ok else "FAIL", report=report, replay=replay, result_file=value["result_file"])

    # ------------------------------------------------------ lane F follow-up 4
    def case_h01(self) -> None:
        commands = ("verify-manifest", "install", "init", "review", "status", "accept", "evidence", "upgrade",
                    "verify-retained", "upgrade-status")
        texts = {"top": text(self.ssh(f"{self.facts['driver']} --help", check=True).stdout)}
        for name in commands:
            texts[name] = text(self.ssh(f"{self.facts['driver']} {name} --help", check=True).stdout)
        leaks = sorted(name for name, value in texts.items()
                       if "SUPPRESS" in value or "_review-unit" in value or "_accept-unit" in value)
        undocumented = {name: self.undocumented_options(value) for name, value in texts.items()}
        undocumented = {name: value for name, value in undocumented.items() if value}
        root_wording = "need root" in texts["top"] and "verify-manifest and upgrade-status do not" in texts["top"]
        ok = not leaks and not undocumented and root_wording and all(name in texts["top"] for name in commands)
        self.record("PASS" if ok else "FAIL", leaks=leaks, undocumented=undocumented, root_wording=root_wording,
                    top_help=texts["top"][-1500:])

    @staticmethod
    def undocumented_options(help_text: str) -> list[str]:
        lines, bad, inside = help_text.splitlines(), [], False
        for index, line in enumerate(lines):
            if line.strip() in ("options:", "optional arguments:"):
                inside = True
                continue
            if inside and line and not line.startswith(" "):
                inside = False
            if inside and line.startswith("  -"):
                described = len([part for part in line.strip().split("  ") if part.strip()]) >= 2
                following = lines[index + 1] if index + 1 < len(lines) else ""
                continued = following.startswith(" " * 8) and not following.strip().startswith("-")
                if not (described or continued):
                    bad.append(line.strip())
        return bad

    def hostile_kits(self) -> dict[str, dict[str, Any]]:
        """Altered copies of the bundle's kit, each with an attacker-consistent
        manifest and SHA256SUMS (the hostile review's F1 shape)."""
        bundle = self.args.bundle_dir
        [kit] = [p for p in bundle.iterdir() if p.name.startswith("cohort-kit-") and p.name.endswith(".tar.gz")]
        top = kit.name.removesuffix(".tar.gz")
        with tarfile.open(kit, "r:gz") as tar:
            members = [(m, tar.extractfile(m).read() if m.isfile() else None) for m in tar.getmembers()]
        info = json.loads(dict((m.name, d) for m, d in members)[f"{top}/BUILD-INFO.json"])
        manifest = json.loads((bundle / "cohort-manifest.json").read_text())
        planted = (b"import os\nopen('/tmp/hostile-kit-shadow-marker-f4', 'a').write("
                   b"f'uid={os.getuid()} planted setup/json.py imported\\n')\n")
        driver_name = f"{top}/setup/constellation_cohort.py"
        variants: dict[str, dict[str, Any]] = {
            "kit-planted-json": {"add": {f"{top}/setup/json.py": planted}, "expect": "kit.unlisted_member"},
            "kit-zero-commit": {"commit": "0" * 40, "expect": "pin.kit_commit"},
            "kit-altered-driver": {"replace": {driver_name: dict((m.name, d) for m, d in members)[driver_name]
                                               + b"\n# altered by the hostile harness\n"},
                                   "expect": "kit.driver_differs"},
        }
        out = self.state / "hostile-kits"
        for name, variant in variants.items():
            files = [(m, variant.get("replace", {}).get(m.name, d)) for m, d in members]
            changed = dict(info)
            if "commit" in variant:
                changed["source_commit"] = variant["commit"]
            if "replace" in variant:
                changed["files"] = {**info["files"], **{key.split("/", 1)[1]: "sha256:" + hashlib.sha256(value).hexdigest()
                                                         for key, value in variant["replace"].items()}}
            files = [(m, (json.dumps(changed, sort_keys=True, indent=1) + "\n").encode()
                      if m.name == f"{top}/BUILD-INFO.json" else d) for m, d in files]
            for path, data in variant.get("add", {}).items():
                extra = tarfile.TarInfo(path)
                extra.mode, extra.mtime, extra.uname, extra.gname = 0o644, 1700000000, "root", "root"
                files.append((extra, data))
            buffer = __import__("io").BytesIO()
            with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for member, data in files:
                    if data is not None:
                        member = __import__("copy").copy(member)
                        member.size = len(data)
                    tar.addfile(member, __import__("io").BytesIO(data) if data is not None else None)
            import gzip
            compressed = gzip.compress(buffer.getvalue(), mtime=0)
            directory = out / name
            directory.mkdir(parents=True)
            (directory / kit.name).write_bytes(compressed)
            value = json.loads(json.dumps(manifest))
            for entry in value["components"]:
                if entry["component"] == "cohort-kit":
                    entry["artifact_sha256"] = "sha256:" + hashlib.sha256(compressed).hexdigest()
                    if "commit" in variant:
                        entry["source_commit"] = variant["commit"]
            (directory / "cohort-manifest.json").write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")
            variant.update(directory=directory, kit_sha256="sha256:" + hashlib.sha256(compressed).hexdigest(),
                           own_driver=True)
        # The hostile review's own kits (built from kit 0.3.0), as it left them.
        for name in ("k1", "k2", "k3"):
            source = self.args.hostile_review_dir / name
            if not source.is_dir():
                continue
            directory = out / f"review-{name}"
            directory.mkdir(parents=True)
            for path in source.iterdir():
                if path.is_file():
                    shutil.copyfile(path, directory / path.name)
            variants[f"review-{name}"] = {"directory": directory, "expect": "pin.incompatible", "own_driver": False}
        for variant in variants.values():
            directory = variant["directory"]
            sums = "".join(f"{file_digest(path)}  {path.name}\n" for path in sorted(directory.iterdir()))
            (directory / "SHA256SUMS").write_text(sums)  # attacker-regenerated
        return variants

    def case_k02(self) -> None:
        variants = self.hostile_kits()
        observed, ok = {}, True
        for name, variant in variants.items():
            guest_dir = f"{GUEST_HOME}/atk/{name}"
            self.ssh(f"mkdir -p {guest_dir}", check=True)
            self.scp_to(sorted(p for p in variant["directory"].iterdir() if p.is_file()), f"{guest_dir}/")
            self.ssh(f"for f in {BUNDLE}/*.deb {BUNDLE}/*.tar.gz; do case $(basename $f) in cohort-kit-*) ;; "
                     f"*) ln $f {guest_dir}/ ;; esac; done", check=True)
            anchored = self.anchored_check(guest_dir)
            bundle_sums = self.ssh(f"cd {guest_dir} && sha256sum --check --strict SHA256SUMS")
            result = self.refuses_without_writes(f"{guest_dir}/cohort-manifest.json", guest_dir, variant["expect"], "",
                                                 cohort=f"qual-{name[:20]}")
            entry = {"published_check_exit": anchored.returncode,
                     "published_check": text(anchored.stdout).strip().splitlines(),
                     "attacker_sha256sums_exit": bundle_sums.returncode, "genuine_driver": result}
            case_ok = anchored.returncode != 0 and result["ok"]
            if variant["own_driver"]:
                # The newcomer who skipped step 1 runs the altered kit's own driver.
                [kit_name] = [p.name for p in variant["directory"].iterdir() if p.name.startswith("cohort-kit-")]
                top = kit_name.removesuffix(".tar.gz")
                self.ssh(f"mkdir -p {guest_dir}/x && tar -xzf {guest_dir}/{kit_name} -C {guest_dir}/x --no-same-owner",
                         check=True)
                own = f"/usr/bin/python3.11 -I -S {guest_dir}/x/{top}/setup/constellation_cohort.py"
                verify = self.ssh(f"{own} verify-manifest --manifest {guest_dir}/cohort-manifest.json "
                                  f"--artifacts {guest_dir}")
                verify_value = json.loads(verify.stdout) if verify.stdout.strip() else {}
                entry["own_driver_verify"] = {"exit": verify.returncode, "result": verify_value.get("result"),
                                              "code": verify_value.get("code")}
                if name == "kit-altered-driver":
                    # Attacker code: only README step 1 can catch it, and it did.
                    entry["own_driver_note"] = ("the altered driver is attacker code and accepts its own kit; "
                                                "the published-digest check (step 1) is the defence and failed it")
                else:
                    before = self.writes_snapshot()
                    install = self.ssh(f"sudo {own} install --cohort qual-own-{name[4:14]} --manifest "
                                       f"{guest_dir}/cohort-manifest.json --artifacts {guest_dir}")
                    install_value = json.loads(install.stdout) if install.stdout.strip() else {}
                    entry["own_driver_install"] = {"exit": install.returncode, "code": install_value.get("code"),
                                                   "writes_unchanged": before == self.writes_snapshot()}
                    case_ok &= (verify.returncode == 2 and verify_value.get("code") == variant["expect"]
                                and install.returncode == 2 and install_value.get("code") == variant["expect"]
                                and entry["own_driver_install"]["writes_unchanged"])
            observed[name] = entry
            ok &= case_ok
        markers = {path: self.ssh(f"test -e {path}").returncode == 0 for path in HOSTILE_MARKERS}
        ok &= not any(markers.values())
        self.record("PASS" if ok else "FAIL", variants=observed, shadow_markers_present=markers,
                    expected={name: variant["expect"] for name, variant in variants.items()})

    def case_t01(self) -> None:
        self.passed("I-04")
        evil = self.args.hostile_review_dir / "evd" / "docket-evil.tar.gz"
        if not evil.is_file():
            raise Refusal(f"the hostile review's substitute docket is absent: {evil}")
        docket = "docket-0.1.0-linux-amd64.tar.gz"
        static, race, stage = f"{GUEST_HOME}/t01-static", f"{GUEST_HOME}/t01-race", f"{GUEST_HOME}/t01-stage"
        self.ssh(f"mkdir -p {static} {race} {stage}", check=True)
        self.scp_to([evil], f"{stage}/")
        forged_info = text(self.ssh(f"cd {stage} && tar -xzOf docket-evil.tar.gz --wildcards '*/bin/docket' | sh -s -- "
                                    "--build-info").stdout).strip()
        self.ssh(f"for f in {BUNDLE}/*.deb {BUNDLE}/*.tar.gz; do case $(basename $f) in {docket}) ;; "
                 f"*) ln $f {static}/ ;; esac; done && cp {stage}/docket-evil.tar.gz {static}/{docket} && "
                 f"cp {BUNDLE}/cohort-manifest.json {static}/", check=True)
        static_result = self.refuses_without_writes(f"{static}/cohort-manifest.json", static, "artifact.missing",
                                                    "docket", cohort="qual-t01-static")
        # The race: swap the docket tarball back and forth while install runs.
        self.ssh(f"for f in {BUNDLE}/*.deb {BUNDLE}/*.tar.gz; do case $(basename $f) in {docket}) ;; "
                 f"*) ln $f {race}/ ;; esac; done && cp {BUNDLE}/{docket} {stage}/genuine && "
                 f"cp {stage}/docket-evil.tar.gz {stage}/evil && cp {BUNDLE}/{docket} {race}/ && "
                 f"cp {BUNDLE}/cohort-manifest.json {race}/", check=True)
        loop = (f"n=0; while [ ! -e {stage}/stop ]; do cp {stage}/evil {stage}/t && mv -f {stage}/t {race}/{docket}; "
                f"cp {stage}/genuine {stage}/t && mv -f {stage}/t {race}/{docket}; n=$((n+1)); done; echo $n > {stage}/swaps")
        self.ssh(f"(setsid nohup sh -c {shlex.quote(loop)} > /dev/null 2>&1 &)", check=True)
        status, install = self.driver(f"install --cohort qual-t01 --manifest {race}/cohort-manifest.json "
                                      f"--artifacts {race}", timeout=900)
        self.ssh(f"touch {stage}/stop; for i in $(seq 50); do [ -s {stage}/swaps ] && break; sleep 0.1; done", check=True)
        swaps = text(self.ssh(f"cat {stage}/swaps", check=True).stdout).strip()
        genuine_docket = self.guest_json("sudo cat /opt/constellation/cohorts/qual-a/installed.json")["identities"]
        genuine_sha = {path.rsplit("/", 1)[1]: value["sha256"] for path, value in genuine_docket.items()
                       if "/cohorts/qual-a/docket/" in path}
        outcome: dict[str, Any] = {"exit": status, "result": install.get("result"), "code": install.get("code"),
                                   "detail": str(install.get("detail", ""))[:300], "swaps_during_install": swaps}
        if status == 0:
            installed = self.guest_json("sudo cat /opt/constellation/cohorts/qual-t01/installed.json")["identities"]
            got = {path.rsplit("/", 1)[1]: value["sha256"] for path, value in installed.items()
                   if "/cohorts/qual-t01/docket/" in path}
            outcome.update(installed_docket=got, equals_genuine=got == genuine_sha)
            race_ok = got == genuine_sha
        else:
            race_ok = install.get("code") in ("artifact.missing", "artifact.changed")
        ok = static_result["ok"] and race_ok and "3093def" in forged_info
        self.record("PASS" if ok else "FAIL", forged_build_info=forged_info[:400], static=static_result, race=outcome,
                    note="either outcome of the race passes if the forged bytes are never installed")

    def case_s01(self) -> None:
        self.passed("I-05")
        done = self.ssh(f"{self.facts['driver']} status --cohort {COHORTS['A'][0]}")
        try:
            value = json.loads(done.stdout)
        except ValueError:
            value = {"stdout": text(done.stdout)[-500:]}
        ok = (done.returncode == 2 and value.get("code") == "host.not_root" and b"Traceback" not in done.stderr
              and len(text(done.stdout).strip().splitlines()) == 1)
        self.record("PASS" if ok else "FAIL", exit=done.returncode, result=value, stderr=text(done.stderr)[-500:])

    def case_s03(self) -> None:
        self.passed("W-04")
        value = self.status(COHORTS["A"][0])
        counters, at_review = value.get("counters", {}), value.get("review", {}).get("counters_at_review", {})
        ok = (counters.get("ag_spends") == 1 and counters.get("docket_attempts") == 1
              and counters.get("settlements") == 1 and counters.get("result_files") == 1
              and all(v == 0 for v in at_review.values()) and len(at_review) == 5
              and value.get("acceptance", {}).get("accepted") is True and "Settled" in value.get("next", ""))
        self.record("PASS" if ok else "FAIL", counters=counters, counters_at_review=at_review, next=value.get("next"))

    def case_s04(self) -> None:
        self.passed("N-09")
        cohort = COHORTS["C"][0]
        waited, deadline = 0.0, {}
        started = time.monotonic()
        while time.monotonic() - started < 420:
            deadline = self.status(cohort).get("acceptance", {}).get("deadline", {})
            if deadline.get("expired"):
                break
            pause = min(30, max(1, deadline.get("seconds_remaining", 30) + 1))
            time.sleep(pause)
            waited += pause
        candidate = self.facts.get("candidate_c")
        status, result = self.driver(f"accept --cohort {cohort} --candidate-sha256 {candidate}")
        claimed = self.ssh(f"sudo test -e /var/lib/constellation/cohorts/{cohort}/driver/accept.claimed.json").returncode == 0
        ok = (deadline.get("expired") is True and status == 2 and result.get("code") == "review.expired"
              and not claimed)
        self.record("PASS" if ok else "FAIL", deadline=deadline, waited_s=round(waited, 1), result=result,
                    accept_claimed=claimed)

    def dpkg_verify(self) -> dict[str, Any]:
        done = self.ssh("sudo dpkg --verify nq-ng")
        return {"exit": done.returncode, "lines": text(done.stdout).strip().splitlines()}

    def case_q02(self) -> None:
        self.passed("I-04")
        target = "/usr/share/doc/nq-ng/copyright"
        self.ssh(f"sudo sh -c 'cp -a {target} /root/nq-copyright.orig && printf \"\\nedited by the harness\\n\" >> {target}'",
                 check=True)
        verify = self.dpkg_verify()
        result = self.refuses_without_writes(f"{BUNDLE}/cohort-manifest.json", BUNDLE, "nq.installed_mismatch",
                                             "copyright", cohort="qual-q02", verify=False)
        self.ssh(f"sudo cp -a /root/nq-copyright.orig {target}", check=True)
        restored = self.dpkg_verify()
        ok = result["ok"] and verify["lines"] and not restored["lines"]
        self.record("PASS" if ok else "FAIL", dpkg_verify_after_edit=verify, install=result,
                    dpkg_verify_after_restore=restored,
                    note="dpkg --verify reports the edit (exit shown); the driver parses its output and compares files")

    def case_q01(self) -> None:
        self.passed("I-04")
        forge = ("rm -rf /root/forged && dpkg-deb -R {deb} /root/forged && "
                 "printf '\\nforged by the harness\\n' >> /root/forged/usr/share/doc/nq-ng/README.md && "
                 "cd /root/forged && find . -path ./DEBIAN -prune -o -type f -printf '%P\\0' | xargs -0 md5sum "
                 "> DEBIAN/md5sums && dpkg-deb --root-owner-group -b /root/forged /root/nq-ng-forged.deb >/dev/null && "
                 "dpkg -i /root/nq-ng-forged.deb >/dev/null").format(deb=f"{BUNDLE}/nq-ng_0.2.0_amd64.deb")
        self.ssh(f"sudo sh -c {shlex.quote(forge)}", check=True)
        forged_sha = text(self.ssh("sudo sha256sum /root/nq-ng-forged.deb", check=True).stdout).split()[0]
        state = text(self.ssh("dpkg-query -W -f='${Status} ${Version}' nq-ng", check=True).stdout)
        verify = self.dpkg_verify()
        result = self.refuses_without_writes(f"{BUNDLE}/cohort-manifest.json", BUNDLE, "nq.installed_mismatch",
                                             "README.md", cohort="qual-q01", verify=False)
        self.ssh(f"sudo dpkg -i {BUNDLE}/nq-ng_0.2.0_amd64.deb >/dev/null", check=True)
        restored = self.dpkg_verify()
        ok = (result["ok"] and not verify["lines"] and verify["exit"] == 0 and state == "install ok installed 0.2.0"
              and not restored["lines"] and forged_sha != "9e953e88d1f79cffd03e97b530199459b5e45ead55ea4ba7d5066e0851008d7b")
        self.record("PASS" if ok else "FAIL", forged_deb_sha256=forged_sha, dpkg_state=state,
                    dpkg_verify_forged=verify, install=result, dpkg_verify_after_restore=restored,
                    note="the forged package has consistent md5sums, so dpkg --verify is clean; the file comparison "
                         "with the pinned package refuses it")

    # ------------------------------------------------------------------- main
    def execute_all(self) -> None:
        self.run_case("I-01", self.case_i01)
        if self.results["I-01"]["outcome"] != "PASS":
            raise Refusal("guest did not boot")
        for cid, function in (("I-02", self.case_i02), ("I-03", self.case_i03), ("H-01", self.case_h01),
                              ("N-01", self.case_n01), ("N-02", self.case_n02), ("N-03", self.case_n03),
                              ("N-04", self.case_n04), ("K-02", self.case_k02), ("I-04", self.case_i04),
                              ("T-01", self.case_t01), ("I-05", self.case_i05), ("S-01", self.case_s01),
                              ("N-05", self.case_n05), ("F-01", self.case_f01), ("W-01", self.case_w01),
                              ("W-02", self.case_w02), ("N-06", self.case_n06), ("W-03", self.case_w03),
                              ("W-04", self.case_w04), ("S-03", self.case_s03), ("N-07", self.case_n07),
                              ("W-05", self.case_w05), ("V-01", self.case_v01), ("K-01", self.case_k01),
                              ("N-08", self.case_n08), ("N-09", self.case_n09), ("S-04", self.case_s04),
                              ("Q-02", self.case_q02), ("Q-01", self.case_q01)):
            self.run_case(cid, function)
        self.ssh("pkill -f fixture_responses_endpoint.py || true")

    def main(self) -> int:
        try:
            self.out.mkdir(parents=True, exist_ok=True)
            self.preflight()
        except Refusal as error:
            print(f"refused: {error}", file=sys.stderr)
            if (self.out / "cases").is_dir():
                self.write_results()
            return 2
        status = 0
        try:
            self.execute_all()
        except Exception as error:  # noqa: BLE001
            self.log(f"harness stopped: {type(error).__name__}: {error}")
            if self.current is not None:
                self.record("FAIL", error=f"{type(error).__name__}: {error}", note="harness stopped")
            for entry in self.results.values():
                if entry["outcome"] == "NOT_EXERCISED" and entry.get("reason") == "not reached":
                    entry["reason"] = f"harness aborted: {error}"[:500]
            status = 1
        finally:
            try:
                self.destroy()
            finally:
                self.write_results()
        summary = {o: sum(1 for r in self.results.values() if r["outcome"] == o) for o in ("PASS", "FAIL", "NOT_EXERCISED")}
        self.log(f"done: {summary}")
        return status if summary["FAIL"] == 0 else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bundle-dir", type=pathlib.Path, required=True,
                   help="release bundle from compose_bundle.py: cohort-manifest.json, artifacts, SHA256SUMS")
    p.add_argument("--output-root", type=pathlib.Path, default=DEFAULT_OUTPUT_ROOT)
    p.add_argument("--output-name", required=True, help="run-NNN")
    p.add_argument("--state-dir", type=pathlib.Path, default=DEFAULT_STATE)
    p.add_argument("--image", type=pathlib.Path, default=DEFAULT_IMAGE)
    p.add_argument("--ssh-port", type=int, default=23451, help="cohort lane range 23451-23459")
    p.add_argument("--vcpus", type=int, default=2)
    p.add_argument("--memory-mib", type=int, default=4096)
    p.add_argument("--keep-guest", action="store_true", help="debugging only: leave the guest running")
    p.add_argument("--published-manifest-sha256", help="trials only: use this instead of README step 1")
    p.add_argument("--hostile-review-dir", type=pathlib.Path, default=pathlib.Path(
        "/tmp/claude-1000/-data-git/95a80b07-250d-4940-af2a-998186e54cb2/scratchpad/h/atk"),
                   help="the lane H hostile review's attack kits (k1-k3) and substitute docket (evd/)")
    p.add_argument("--published-kit-sha256", help="trials only: use this instead of README step 1")
    return p


if __name__ == "__main__":
    sys.exit(Harness(parser().parse_args()).main())
