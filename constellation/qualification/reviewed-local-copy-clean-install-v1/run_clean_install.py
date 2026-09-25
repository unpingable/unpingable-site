#!/usr/bin/env python3
"""Clean-install qualification of a reviewed-local-copy/v1 cohort release.

QUALIFICATION-ONLY HARNESS. Nothing here is part of the product path. It boots
one disposable Debian 12 guest from a verified read-only base image (qcow2
overlay, cloud-init seed, user networking with restrict=on and one SSH
hostfwd on 127.0.0.1, qemu -sandbox on), copies in only the release bundle
(cohort manifest, artifacts, SHA256SUMS, and the qualification-only fixture
tooling) and the harness's guest scripts, and runs the documented newcomer
steps with the driver extracted from the bundle's cohort-kit artifact:

    verify-manifest -> install -> init (fixture-review) -> review -> status
    -> SYNTHETIC OPERATOR accept -> status -> evidence

plus refusal cases, each on its own cohort where it consumes an occurrence.
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
GUEST_SCRIPTS = ("probe.sh", "expire_issuance.py")
HARNESS_FILES = ("run_clean_install.py", "compose_bundle.py", "verify_cohort_evidence.py",
                 *(f"guest/{name}" for name in GUEST_SCRIPTS))
IMAGE_NAME = "debian-12-genericcloud-amd64-20260903-2590.qcow2"
DEFAULT_IMAGE = pathlib.Path(
    "/data/git/.campaign-artifacts/constellation-operator-beta-composed-m2-run-002/input"
) / IMAGE_NAME
DEFAULT_OUTPUT_ROOT = pathlib.Path("/data/git/.campaign-artifacts/alpha-exit-closure-20260925/cohort-clean-install")
DEFAULT_STATE = pathlib.Path.home() / ".local/state/alpha-exit-cohort-clean-install"
GUEST_USER = "cohortqual"
GUEST_HOME = f"/home/{GUEST_USER}"
KIT = f"{GUEST_HOME}/kit"
BUNDLE = f"{GUEST_HOME}/bundle"
FIXTURE = f"{GUEST_HOME}/fixture"
EVIDENCE = "/root/cohort-evidence"
# Cohorts: A is the newcomer path; B the stale fixture review; C the expired issuance.
COHORTS = {"A": ("qual-a", 18431, "accepted"), "B": ("qual-b", 18432, "stale"), "C": ("qual-c", 18433, "accepted")}

CASES = (
    ("P-01", "preflight: tools, KVM, base image SHA-512, free port, bundle SHA256SUMS"),
    ("I-01", "boot a fresh Debian 12 guest; copy the bundle; sha256sum --check; extract only the cohort kit"),
    ("I-02", "host facts the driver depends on (python3.11, openssl Ed25519, systemd-run, setpriv)"),
    ("I-03", "driver unit tests from the extracted kit under the guest's python3.11 -I -S"),
    ("N-01", "a manifest naming a wrong artifact digest refuses (verify-manifest and install), writing nothing"),
    ("N-02", "an artifact whose bytes differ from the manifest digest refuses, writing nothing"),
    ("N-03", "a manifest naming another source commit refuses (pin.incompatible)"),
    ("N-04", "install refuses as a non-root account"),
    ("I-04", "verify-manifest and install: every pin, artifact digest and build info checked"),
    ("I-05", "init fixture-review: account, synthetic identities and keys, codex home, plan, ports, NQ watcher"),
    ("N-05", "re-running init on the existing cohort refuses and changes nothing"),
    ("F-01", "loopback fixture endpoint (qualification-only tooling) on guest 127.0.0.1"),
    ("W-01", "review: one durable unit, fresh observation, AG genesis, one bounded fixture review, stops before acceptance"),
    ("W-02", "status: retained candidate digest; zero grants, spends, attempts, effects"),
    ("W-03", "SYNTHETIC OPERATOR acceptance of the exact candidate digest (harness step, labelled)"),
    ("W-04", "status after execution: settled success, result.txt written once with the reviewed bytes"),
    ("W-05", "evidence: bundle exported; driver join complete; independent verifier (alpha.6 shape) passes on the host"),
    ("N-06", "accept naming a digest other than the retained candidate refuses with no grant or effect"),
    ("N-07", "a second execute attempt refuses: driver accept, the kit continuation and AG re-run; one effect"),
    ("N-08", "stale fixture review (cohort B) is refused before any candidate; no authority, no effect"),
    ("N-09", "expired issuance (cohort C) is never presented: AG refuses dispatch; no Docket record, no effect"),
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
        self.record("PASS", image_sha512=actual, bundle=self.identity["bundle"])

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
        self.ssh(f"mkdir -p {GUEST_HOME}/bin {KIT} {BUNDLE}/qualification-only {FIXTURE}", check=True)
        self.scp_to([HERE / "guest" / name for name in GUEST_SCRIPTS], f"{GUEST_HOME}/bin/")
        bundle = self.args.bundle_dir
        self.scp_to(sorted(p for p in bundle.iterdir() if p.is_file()), f"{BUNDLE}/")
        self.scp_to(sorted((bundle / "qualification-only").iterdir()), f"{BUNDLE}/qualification-only/")
        # Newcomer step 1: check the bundle, then extract only the cohort kit.
        self.ssh(f"cd {BUNDLE} && sha256sum --check --strict SHA256SUMS", check=True)
        kit = [p.name for p in bundle.iterdir() if p.name.startswith("cohort-kit-") and p.name.endswith(".tar.gz")]
        if len(kit) != 1:
            raise Refusal("bundle must hold exactly one cohort-kit tarball")
        self.ssh(f"tar -xzf {BUNDLE}/{kit[0]} -C {KIT} --no-same-owner", check=True)
        top = kit[0].removesuffix(".tar.gz")
        self.facts["kit_root"] = f"{KIT}/{top}"
        self.facts["driver"] = f"/usr/bin/python3.11 -I -S {KIT}/{top}/setup/constellation_cohort.py"
        version = self.ssh(f"{self.facts['driver']} --version", check=True).stdout.strip()
        fixture = sorted((bundle / "qualification-only").iterdir())[0].name
        self.ssh(f"tar -xzf {BUNDLE}/qualification-only/{fixture} -C {FIXTURE} --no-same-owner", check=True)
        self.ssh(f"chmod 0755 {GUEST_HOME}/bin/*", check=True)
        self.record("PASS", os=release.decode(), driver_version=text(version), kit=kit[0],
                    fixture_tooling=fixture, note="fixture tooling is a qualification-only dependency")

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
        done = self.ssh(f"/usr/bin/python3.11 -I -S -B {self.facts['kit_root']}/setup/test_constellation_cohort.py -v 2>&1")
        tail = text(done.stdout).strip().splitlines()[-3:]
        ok = done.returncode == 0 and any(line.startswith("OK") for line in tail)
        self.record("PASS" if ok else "FAIL", summary=tail)

    # -------------------------------------------------------- manifest refusals
    def variant_manifest(self, name: str, component: str, field: str, value: str) -> str:
        path = f"{GUEST_HOME}/{name}.json"
        code = ("import json,sys; m=json.load(open(sys.argv[1])); "
                "[e.update({sys.argv[3]: sys.argv[4]}) for e in m['components'] if e['component']==sys.argv[2]]; "
                "open(sys.argv[5],'w').write(json.dumps(m))")
        self.ssh(f"/usr/bin/python3.11 -I -S -c {shlex.quote(code)} {BUNDLE}/cohort-manifest.json {component} "
                 f"{field} {shlex.quote(value)} {path}", check=True)
        return path

    def refuses_without_writes(self, manifest: str, artifacts: str, expected: str, fragment: str) -> dict:
        before = self.writes_snapshot()
        status_v, verify = self.driver(f"verify-manifest --manifest {manifest} --artifacts {artifacts}")
        status_i, install = self.driver(f"install --cohort qual-refused --manifest {manifest} --artifacts {artifacts}")
        after = self.writes_snapshot()
        ok = (status_v == 2 and verify.get("code") == expected and fragment in verify.get("detail", "")
              and status_i == 2 and install.get("code") == expected and before == after)
        return {"ok": ok, "verify": verify, "install": install, "writes_unchanged": before == after}

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
        ok = (status_v == 0 and verify.get("qualified_cohort") == "alpha-exit-rc"
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
        ok = (review.get("candidate_sha256") == self.facts["candidate_sha256"]
              and all(review.get(key) == 0 for key in ("grants", "spends", "docket_attempts", "executor_calls", "effects"))
              and value["native"].get("program_counter") == "proposal_recorded"
              and value["result_file"].get("present") is False)
        self.record("PASS" if ok else "FAIL", status=value)

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
        verifier = run([sys.executable, str(HERE / "verify_cohort_evidence.py"), "--evidence", str(target)], check=False)
        (self.out / "evidence" / "qual-a-verifier.json").write_bytes(verifier.stdout)
        verified = json.loads(verifier.stdout) if verifier.returncode == 0 else {"stderr": text(verifier.stderr)[-2000:]}
        ok = status == 0 and result.get("join_complete") is True and verifier.returncode == 0 \
            and verified.get("result") == "passed"
        self.record("PASS" if ok else "FAIL", evidence=result, verifier=verified)

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
        code = (f"import sys; sys.path[:0]=[{kit + '/setup'!r}, {kit!r}]; import continue_reviewed_action as c; "
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

    # ------------------------------------------------------------------- main
    def execute_all(self) -> None:
        self.run_case("I-01", self.case_i01)
        if self.results["I-01"]["outcome"] != "PASS":
            raise Refusal("guest did not boot")
        for cid, function in (("I-02", self.case_i02), ("I-03", self.case_i03), ("N-01", self.case_n01),
                              ("N-02", self.case_n02), ("N-03", self.case_n03), ("N-04", self.case_n04),
                              ("I-04", self.case_i04), ("I-05", self.case_i05), ("N-05", self.case_n05),
                              ("F-01", self.case_f01), ("W-01", self.case_w01), ("W-02", self.case_w02),
                              ("N-06", self.case_n06), ("W-03", self.case_w03), ("W-04", self.case_w04),
                              ("N-07", self.case_n07), ("W-05", self.case_w05), ("N-08", self.case_n08),
                              ("N-09", self.case_n09)):
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
    return p


if __name__ == "__main__":
    sys.exit(Harness(parser().parse_args()).main())
