#!/usr/bin/env python3
"""Clean-install qualification of a reviewed-local-copy/v1 cohort release.

QUALIFICATION-ONLY HARNESS. Nothing here is part of the product path. It boots
one disposable Debian 12 guest from a verified read-only base image (qcow2
overlay, cloud-init seed, user networking with restrict=on and one SSH
hostfwd on 127.0.0.1, qemu -sandbox on), copies in only the release bundle
(cohort manifest, artifacts, SHA256SUMS) and the harness's own guest scripts,
and runs the newcomer steps with the cohort setup driver from the bundle's
cohort-kit artifact:

    install -> init (fixture-review) -> review -> SYNTHETIC OPERATOR accept
    -> status -> evidence

plus refusal cases. The acceptance step is performed by this harness as a
labelled synthetic operator (case W-03), never by the driver: the driver has
no automatic-acceptance option. The fixture-review route qualifies install,
wiring, custody, authority and effect; never review independence. The real
provider route is an operator-run qualification and is refused here.

Every case ends PASS, FAIL or NOT_EXERCISED with the observed output; nothing
is relabelled. Cases that need component artifacts not yet published are
NOT_EXERCISED with the pending lane named. Modelled on NQ
qualification/release-closure-v1/run_acceptance.py.

Phase-1 mode (`--phase1-kit-dir`): with no release bundle yet, copy the driver
and its unit tests from a kit directory as a labelled stand-in, and run only
the host-facts, unit-test and fail-closed cases.
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
import time
import traceback
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
GUEST_SCRIPTS = ("probe.sh",)
HARNESS_FILES = ("run_clean_install.py", *(f"guest/{name}" for name in GUEST_SCRIPTS))
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
DRIVER = f"/usr/bin/python3 -I {KIT}/constellation_cohort.py"
COHORT = "qual-a"
FIXTURE_PORT = 23459  # guest loopback only; not forwarded

CASES = (
    ("P-01", "preflight: tools, KVM, base image SHA-512, free port, bundle SHA256SUMS"),
    ("I-01", "boot: fresh Debian 12 guest from the verified image"),
    ("I-02", "host facts the driver depends on (python3.11, openssl Ed25519, systemd-run, setpriv)"),
    ("I-03", "driver unit tests under the guest's /usr/bin/python3"),
    ("I-04", "install: cohort manifest verified, artifacts installed, build info matches every pin"),
    ("I-05", "init fixture-review: account, synthetic identities and keys, config, plan, AG genesis"),
    ("F-01", "fixture review endpoint (lane E artifact) listening on guest loopback only"),
    ("W-01", "review: one durable unit, fresh observation, one bounded fixture review, stops before acceptance"),
    ("W-02", "status: retained candidate digest and zero grants, spends, attempts, effects"),
    ("W-03", "SYNTHETIC OPERATOR acceptance of the exact candidate digest (harness step, labelled)"),
    ("W-04", "status after execution: settled, exact result.txt bytes, one effect"),
    ("W-05", "evidence: bundle written and joins verified"),
    ("N-01", "verify-manifest refuses a manifest whose pins are not a qualified cohort, writing nothing"),
    ("N-02", "install refuses as a non-root account"),
    ("N-03", "install refuses an artifact whose bytes differ from the manifest digest"),
    ("N-04", "install refuses a debug build or a build-info commit mismatch"),
    ("N-05", "a second init of the same cohort refuses"),
    ("N-06", "accept with a digest other than the retained candidate refuses with no grant or effect"),
    ("N-07", "fixture-review stale review (currentness exceeded) refuses without permission"),
)
PENDING = {
    "I-04": "pending: release artifacts from lanes A, B, C, D, E and NQ-P",
    "I-05": "pending: lanes A (ag-loopctl, standing sealer), B (docket), C (maude-plan.pyz), NQ-P (account model)",
    "F-01": "pending: lane E loopback fixture artifact",
    "W-01": "pending: I-05 and F-01",
    "W-02": "pending: W-01",
    "W-03": "pending: W-02",
    "W-04": "pending: W-03",
    "W-05": "pending: W-04 and the lane A/B evidence join verifier",
    "N-03": "pending: needs a qualified cohort entry in the driver (pins are PENDING, so N-01 refuses first)",
    "N-04": "pending: release artifacts",
    "N-05": "pending: I-05",
    "N-06": "pending: W-02",
    "N-07": "pending: F-01 scripted stale mode",
}


class Refusal(Exception):
    """A precondition or harness invariant that stops the run."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_digest(path: pathlib.Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, check: bool = True, timeout: float | None = 600) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
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
        self.guest: Guest | None = None
        self.identity: dict[str, Any] = {}
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
            "mode": "phase1-kit-stand-in" if self.args.phase1_kit_dir else "release-bundle",
            "harness": self.identity.get("harness"),
            "invocation": sys.argv,
            "started_at": self.started,
            "updated_at": utc_now(),
            "bundle": self.identity.get("bundle"),
            "base_image": self.identity.get("image"),
            "guest": {"name": self.guest.name, "ssh_port": self.guest.port, "qemu_command": self.guest.command}
            if self.guest else None,
            "guest_facts": self.identity.get("guest_facts"),
            "summary": {o: sum(1 for r in self.results.values() if r["outcome"] == o)
                        for o in ("PASS", "FAIL", "NOT_EXERCISED")},
            "cases": [self.results[cid] for cid, _ in CASES],
        }
        tmp = self.out / "CLEAN-INSTALL-RESULT.json.tmp"
        tmp.write_text(json.dumps(document, indent=2, default=str) + "\n", encoding="utf-8")
        os.replace(tmp, self.out / "CLEAN-INSTALL-RESULT.json")

    def begin(self, cid: str) -> None:
        self.current = cid
        self.log(f"== {cid} {dict(CASES)[cid]}")
        self.append_case(f"# {cid} {dict(CASES)[cid]}\n# started {utc_now()}\n")

    def record(self, outcome: str, **fields: Any) -> None:
        assert self.current is not None
        entry = self.results[self.current]
        entry.pop("reason", None)
        entry.update({"outcome": outcome, "recorded_at": utc_now(), "log": f"cases/{self.current}.log", **fields})
        self.append_case(f"# outcome {outcome} {json.dumps(fields, default=str)}\n")
        self.log(f"   -> {outcome}")
        self.current = None
        self.write_results()

    def run_case(self, cid: str, function, *args: Any) -> None:
        self.begin(cid)
        try:
            function(*args)
        except Refusal as error:
            self.record("FAIL", error=str(error), note="harness refusal during the case")
        except Exception as error:  # noqa: BLE001 - record, never hide
            self.append_case(traceback.format_exc())
            self.record("FAIL", error=f"{type(error).__name__}: {error}", note="unexpected exception")
        if self.current is not None:
            self.record("FAIL", error="case ended without recording an outcome")

    def skip(self, cid: str, reason: str) -> None:
        self.results[cid].update({"outcome": "NOT_EXERCISED", "reason": reason, "recorded_at": utc_now()})
        self.write_results()

    # --------------------------------------------------------------- guest io
    def ssh(self, command: str, *, check: bool = False, timeout: float = 600) -> subprocess.CompletedProcess[bytes]:
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

    def driver_json(self, arguments: str, *, root: bool) -> tuple[int, dict[str, Any]]:
        done = self.ssh(("sudo " if root else "") + f"{DRIVER} {arguments}")
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            raise Refusal(f"driver output is not one JSON object: {text(done.stdout)[-500:]}") from None

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
        if self.args.bundle_dir is not None:
            bundle = self.args.bundle_dir
            checked = subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=bundle,
                                     capture_output=True, text=True, check=False)
            if checked.returncode != 0:
                raise Refusal(f"bundle SHA256SUMS do not verify on the host: {checked.stdout}{checked.stderr}")
            names = [line.split("  ", 1)[1] for line in (bundle / "SHA256SUMS").read_text().splitlines() if line]
            if "cohort-manifest.json" not in names:
                raise Refusal("bundle has no cohort-manifest.json listed in SHA256SUMS")
            self.identity["bundle"] = {"directory": str(bundle),
                                       "sha256sums_sha256": file_digest(bundle / "SHA256SUMS"), "files": names}
        else:
            kit = self.args.phase1_kit_dir
            self.identity["bundle"] = {"mode": "phase1-kit-stand-in", "directory": str(kit),
                                       "files": {name: file_digest(kit / name) for name in
                                                 ("constellation_cohort.py", "test_constellation_cohort.py")}}
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
        # The genericcloud root is about 3 GB; grow the overlay so cloud-init's
        # growpart leaves room for the cohort artifacts and stores.
        run(["qemu-img", "create", "-q", "-f", "qcow2", "-b", str(self.args.image), "-F", "qcow2",
             str(root / "overlay.qcow2"), "12G"])
        self.guest = guest
        return guest

    def start_guest(self, guest: Guest) -> None:
        root = guest.root
        guest.command = [
            "qemu-system-x86_64", "-name", f"{guest.name},process={guest.name}",
            "-no-user-config", "-nodefaults", "-accel", "kvm", "-machine", "q35", "-cpu", "host",
            "-smp", "2", "-m", "3072", "-display", "none", "-monitor", "none",
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
        if (guest.root / "serial.log").exists():
            shutil.copy2(guest.root / "serial.log", self.out / "evidence" / "a-serial.log")
        (guest.root / "overlay.qcow2").unlink(missing_ok=True)

    # ------------------------------------------------------------------ cases
    def case_i01(self) -> None:
        guest = self.prepare_guest()
        self.start_guest(guest)
        self.wait_ssh(guest)
        self.ssh("cloud-init status --wait >/dev/null; cloud-init status", timeout=900)
        release = self.ssh('. /etc/os-release; printf "%s:%s" "$ID" "$VERSION_ID"', check=True).stdout
        if release != b"debian:12":
            raise Refusal(f"not Debian 12: {release!r}")
        self.ssh(f"mkdir -p {GUEST_HOME}/bin {KIT} {BUNDLE}", check=True)
        self.scp_to([HERE / "guest" / name for name in GUEST_SCRIPTS], f"{GUEST_HOME}/bin/")
        if self.args.phase1_kit_dir is not None:
            # LABELLED STAND-IN: in phase 1 the driver comes from the kit source
            # directory, not from a cohort-kit release artifact.
            kit = self.args.phase1_kit_dir
            self.scp_to([kit / "constellation_cohort.py", kit / "test_constellation_cohort.py"], f"{KIT}/")
        else:
            bundle = self.args.bundle_dir
            self.scp_to(sorted(p for p in bundle.iterdir() if p.is_file()), f"{BUNDLE}/")
            self.ssh(f"cd {BUNDLE} && sha256sum --check --strict SHA256SUMS", check=True)
            raise Refusal("release-bundle mode: extracting the cohort-kit artifact is pending (lane F phase 2)")
        self.ssh(f"chmod 0755 {GUEST_HOME}/bin/*.sh", check=True)
        self.record("PASS", os=release.decode())

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
        if missing:
            self.record("FAIL", missing=missing, facts=facts)
        else:
            self.record("PASS", facts=facts)

    def case_i03(self) -> None:
        # -I implies -P on 3.11, so run the test file as a script; it puts its
        # own directory on sys.path explicitly.
        done = self.ssh(f"/usr/bin/python3 -I -B {KIT}/test_constellation_cohort.py -v 2>&1")
        tail = text(done.stdout).strip().splitlines()[-3:]
        if done.returncode == 0 and any(line.startswith("OK") for line in tail):
            self.record("PASS", summary=tail)
        else:
            self.record("FAIL", exit=done.returncode, summary=tail)

    def case_n01(self) -> None:
        # A syntactically valid manifest whose pins are not a qualified cohort.
        self.ssh(f"mkdir -p {GUEST_HOME}/n01/artifacts", check=True)
        make = ("import json,hashlib,sys; sys.path.insert(0,'" + KIT + "'); import constellation_cohort as c; "
                "print(json.dumps({'schema':c.MANIFEST_SCHEMA,'profile':c.PROFILE,'components':["
                "{'component':n,'package_version':'0.0.0','source_commit':hashlib.sha1(n.encode()).hexdigest(),"
                "'artifact_sha256':'sha256:'+hashlib.sha256(n.encode()).hexdigest()} for n in sorted(c.COMPONENTS)]}))")
        self.ssh(f"/usr/bin/python3 -I -c {shlex.quote(make)} > {GUEST_HOME}/n01/manifest.json", check=True)
        before = self.ssh("sudo find /opt /var/lib -maxdepth 2 -name 'constellation*' | sort", check=True).stdout
        status, result = self.driver_json(
            f"verify-manifest --manifest {GUEST_HOME}/n01/manifest.json --artifacts {GUEST_HOME}/n01/artifacts", root=True)
        status_i, result_i = self.driver_json(
            f"install --cohort {COHORT} --manifest {GUEST_HOME}/n01/manifest.json --artifacts {GUEST_HOME}/n01/artifacts",
            root=True)
        after = self.ssh("sudo find /opt /var/lib -maxdepth 2 -name 'constellation*' | sort", check=True).stdout
        ok = (status == 2 and result.get("code") == "pin.incompatible" and status_i == 2
              and result_i.get("code") == "pin.incompatible" and before == after)
        self.record("PASS" if ok else "FAIL", verify=result, install=result_i,
                    writes_before=text(before), writes_after=text(after))

    def case_n02(self) -> None:
        status, result = self.driver_json(
            f"install --cohort {COHORT} --manifest {GUEST_HOME}/n01/manifest.json --artifacts {GUEST_HOME}/n01/artifacts",
            root=False)
        ok = status == 2 and result.get("code") == "host.not_root"
        self.record("PASS" if ok else "FAIL", result=result)

    # ------------------------------------------------------------------- main
    def execute_all(self) -> None:
        self.run_case("I-01", self.case_i01)
        if self.results["I-01"]["outcome"] != "PASS":
            raise Refusal("guest did not boot")
        self.run_case("I-02", self.case_i02)
        self.run_case("I-03", self.case_i03)
        self.run_case("N-01", self.case_n01)
        self.run_case("N-02", self.case_n02)
        for cid, reason in PENDING.items():
            self.skip(cid, reason)

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
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle-dir", type=pathlib.Path,
                        help="release bundle: cohort-manifest.json, artifacts, SHA256SUMS")
    source.add_argument("--phase1-kit-dir", type=pathlib.Path,
                        help="phase 1 only: kit directory holding the driver and its tests (labelled stand-in)")
    p.add_argument("--output-root", type=pathlib.Path, default=DEFAULT_OUTPUT_ROOT)
    p.add_argument("--output-name", default="clean-install-001")
    p.add_argument("--state-dir", type=pathlib.Path, default=DEFAULT_STATE)
    p.add_argument("--image", type=pathlib.Path, default=DEFAULT_IMAGE)
    p.add_argument("--ssh-port", type=int, default=23451, help="cohort lane range 23451-23459")
    p.add_argument("--keep-guest", action="store_true", help="debugging only: leave the guest running")
    return p


if __name__ == "__main__":
    sys.exit(Harness(parser().parse_args()).main())
