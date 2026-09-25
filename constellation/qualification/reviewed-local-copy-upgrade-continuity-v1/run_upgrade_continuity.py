#!/usr/bin/env python3
"""Upgrade and evidence continuity of reviewed-local-copy/v1, cohort A -> B.

QUALIFICATION-ONLY HARNESS (lane G3, alpha-exit closure). It boots one fresh
Debian 12 guest from the verified image (qcow2 overlay, KVM, restrict=on user
networking, one SSH hostfwd on 127.0.0.1, qemu -sandbox on), copies in only
two cohort bundles and this harness's guest helper, and qualifies the
driver's upgrade rule experimentally:

    cohort A (alpha-exit-rc, kit 0.3.0)   install -> init -> review ->
        SYNTHETIC OPERATOR accept -> settled success -> evidence
    cohort B (g3-qual-b, qualification-only: Docket rebuilt with a version
        bump, kit with the upgrade procedure)   install -> upgrade (export,
        retain, quarantine; once interrupted by SIGKILL) -> init -> review
        -> SYNTHETIC OPERATOR accept -> settled success -> evidence

and then shows that A's evidence verifies from the retained copy under B's
tools and on the host with the standalone verifier (digests identical to the
pre-upgrade export), which identities are preserved and which are new,
that nothing of A can take effect under B, that mixed A/B pins refuse, that
tampered retained evidence refuses, and that an interrupted upgrade is
detected without losing A's evidence.

Synthetic identities and keys only; loopback fixture review; no provider
call. Every case ends PASS, FAIL or NOT_EXERCISED with its observed output.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tarfile
import time
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
CLEAN = HERE.parent / "reviewed-local-copy-clean-install-v1"
sys.path.insert(0, str(CLEAN))
import run_clean_install as base  # noqa: E402
from run_clean_install import Blocked, Refusal, file_digest, run, text, utc_now  # noqa: E402

HARNESS_FILES = ("run_upgrade_continuity.py", "compose_cohort_b.py", "guest/g3_guest.py",
                 "../reviewed-local-copy-clean-install-v1/run_clean_install.py")
DEFAULT_OUTPUT_ROOT = pathlib.Path("/data/git/.campaign-artifacts/alpha-exit-closure-20260925/upgrade-continuity")
DEFAULT_STATE = pathlib.Path.home() / ".local/state/alpha-exit-g3-upgrade-continuity"
# Bundle A must be the qualified alpha-exit-rc bundle of cohort-clean-install/run-003.
RUN_003_MANIFEST = "874943a91d43a101176f5331822fd816c46251f51f83d0976777b50f89c8194c"
AG_PIN = {"package_version": "0.1.0", "source_commit": "58122cec1ca8de35a1d146bf7987f8e69f49a040",
          "artifact_sha256": "sha256:bc53b836d7207493bbe35f0b380475641603caf3aedea6e8bcd3c9c0dea6ab5c"}
GH = base.GUEST_HOME
BUNDLE = {"A": f"{GH}/bundle-a", "B": f"{GH}/bundle-b"}
KIT = {"A": f"{GH}/kit-a", "B": f"{GH}/kit-b"}
FIXTURE = f"{GH}/fixture"
HELPER = f"{GH}/bin/g3_guest.py"
COHORT = {"A": ("g3-a", 18461), "B": ("g3-b", 18462)}
WORK = "/root/g3"
EXPORT = {"A": f"{WORK}/a-evidence", "B": f"{WORK}/b-evidence"}
JOURNAL = "/var/lib/constellation/upgrades/g3-a-to-g3-b"
STATE = "/var/lib/constellation/cohorts"
PY = "/usr/bin/python3.11 -I -S"

CASES = (
    ("P-01", "preflight: tools, KVM, image SHA-512, port; bundle A is run-002's; bundle B verifies; Docket B reproducible"),
    ("I-01", "boot a fresh Debian 12 guest; copy both bundles; sha256sum --check; extract both kits"),
    ("I-02", "driver unit tests of both kits under the guest's python3.11 -I -S"),
    ("A-01", "cohort A (kit 0.3.0): install, init, review, SYNTHETIC OPERATOR accept, settled success, result.txt once"),
    ("A-02", "cohort A evidence export (pre-upgrade); standalone host verifier passes"),
    ("M-01", "mixed A/B pins refuse in both drivers (verify-manifest and install), writing nothing"),
    ("B-01", "cohort B (g3-qual-b): verify-manifest and install beside A; Docket B identity; A untouched"),
    ("U-01", "a tampered or padded export is refused by upgrade before any write"),
    ("U-02", "upgrade SIGKILLed partway: detected; successor init and a plain rerun refuse; A's evidence intact"),
    ("U-03", "upgrade after naming the interrupted attempt: verified with B's tools, retained, quarantined, tombstoned"),
    ("U-04", "verify-retained under B's tools; host standalone verifier; digests identical to the pre-upgrade export"),
    ("B-02", "init B: fresh identities and keys, predecessor recorded; identity comparison with A"),
    ("B-03", "cohort B review, SYNTHETIC OPERATOR accept, settled success, evidence; host verifier passes"),
    ("X-01", "A's retained signed issuance presented to B's Docket is refused; B unchanged"),
    ("X-02", "A's issuance re-presented to a copy of A's retained Docket store returns its settled custody; never executes"),
    ("X-03", "A's issuance to a fresh Docket trusting A's key is refused as expired (not-after); no custody"),
    ("X-04", "A's standing and grants do not authorize B, and B's operator cannot grant in A's Docket state"),
    ("X-05", "A's finite-run input against B's AG store refuses; B's AG state unchanged"),
    ("X-06", "the retired cohort id cannot be reinitialized or reviewed by either driver"),
    ("T-01", "a byte-flipped retained copy is refused by verify-retained and by the host verifier"),
    ("T-02", "a tampered retained copy with rewritten SHA256SUMS and marker is refused (journal binding)"),
    ("K-01", "AG replays A's retained store without A's issuer private key; retained state alone exits 3, never "
             "success; verify-retained passes with the quarantined key set aside"),
)


class Harness(base.Harness):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.results = {cid: {"id": cid, "title": title, "outcome": "NOT_EXERCISED", "reason": "not reached"}
                        for cid, title in CASES}

    # ------------------------------------------------------------ records
    def begin(self, cid: str) -> None:
        self.current = cid
        self.case_started = time.monotonic()
        self.log(f"== {cid} {dict(CASES)[cid]}")
        self.append_case(f"# {cid} {dict(CASES)[cid]}\n# started {utc_now()}\n")

    def write_results(self) -> None:
        document = {
            "schema": "constellation.cohort-upgrade-continuity-result/v1",
            "campaign": "alpha-exit-closure-20260925", "lane": "G3", "profile": "reviewed-local-copy/v1",
            "qualification_only": True,
            "review_route": "fixture-review (install, wiring, custody, authority and effect; never review independence)",
            "operator_acceptance": "synthetic operator performed by this harness; not a human attestation",
            "harness": self.identity.get("harness"), "invocation": sys.argv, "started_at": self.started,
            "updated_at": utc_now(), "bundles": self.identity.get("bundles"), "base_image": self.identity.get("image"),
            "guest": {"name": self.guest.name, "ssh_port": self.guest.port, "qemu_command": self.guest.command}
            if self.guest else None,
            "facts": self.facts,
            "summary": {o: sum(1 for r in self.results.values() if r["outcome"] == o)
                        for o in ("PASS", "FAIL", "NOT_EXERCISED")},
            "cases": [self.results[cid] for cid, _ in CASES],
        }
        tmp = self.out / "UPGRADE-CONTINUITY-RESULT.json.tmp"
        tmp.write_text(json.dumps(document, indent=2, default=str) + "\n", encoding="utf-8")
        os.replace(tmp, self.out / "UPGRADE-CONTINUITY-RESULT.json")

    def describe_harness(self) -> dict[str, Any]:
        def git(*arguments: str) -> str | None:
            done = subprocess.run(["git", "-C", str(HERE), *arguments], capture_output=True, text=True, check=False)
            return done.stdout.strip() if done.returncode == 0 else None
        return {"directory": str(HERE), "commit": git("rev-parse", "HEAD"),
                "dirty_paths": (git("status", "--porcelain", "--", ".", str(CLEAN)) or "").splitlines(),
                "files": {name: file_digest(HERE / name) for name in HARNESS_FILES}}

    # ------------------------------------------------------------ helpers
    def drv(self, which: str, arguments: str, *, timeout: float = 900) -> tuple[int, dict[str, Any]]:
        started = time.monotonic()
        done = self.ssh(f"sudo {self.facts['driver_' + which]} {arguments}", timeout=timeout)
        try:
            value = json.loads(done.stdout)
        except ValueError:
            raise Refusal(f"driver output is not one JSON object: {text(done.stdout)[-500:]}"
                          f"{text(done.stderr)[-800:]}") from None
        self.facts.setdefault("driver_calls", []).append(
            {"driver": which, "arguments": arguments.split(" --")[0], "exit": done.returncode,
             "elapsed_s": round(time.monotonic() - started, 2), "result": value.get("result"), "code": value.get("code")})
        return done.returncode, value

    def root_json(self, command: str) -> Any:
        return json.loads(self.ssh(f"sudo {command}", check=True).stdout)

    def snapshot(self) -> str:
        return text(self.ssh("sudo find /opt/constellation /var/lib/constellation /etc/nq /var/lib/nq "
                             "-printf '%p %s %T@ %m %u\\n' 2>/dev/null | sort | sha256sum", check=True).stdout).split()[0]

    def pull(self, guest_dir: str, name: str) -> pathlib.Path:
        archive = self.ssh(f"sudo tar -C {guest_dir} -czf - .", check=True).stdout
        target = self.out / "evidence" / name
        target.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            tar.extractall(target, filter="data")
        return target

    def host_verify(self, directory: pathlib.Path, label: str) -> tuple[int, dict]:
        """The in-kit verifier from bundle A's kit tarball (see P-01), run on the host."""
        code, value, raw = super().host_verify(directory)
        (self.out / "evidence" / f"{label}-verifier.json").write_bytes(raw)
        return code, value

    def installed_program(self, which: str, component: str, relative: str) -> str:
        roots = self.root_json(f"cat /opt/constellation/cohorts/{COHORT[which][0]}/installed.json")["roots"]
        return f"{roots[component]}/{relative}"

    def workflow(self, which: str) -> dict:
        """init was run; review, status, SYNTHETIC OPERATOR accept, status."""
        cohort, port = COHORT[which]
        self.start_fixture(which)
        status, reviewed = self.drv(which, f"review --cohort {cohort}")
        if status != 0:
            raise Refusal(f"review refused: {reviewed}")
        _, before = self.drv(which, f"status --cohort {cohort}")
        candidate = before["review"]["candidate_sha256"]
        # SYNTHETIC OPERATOR: the harness names the digest status printed.
        status, accepted = self.drv(which, f"accept --cohort {cohort} --candidate-sha256 {candidate}")
        _, after = self.drv(which, f"status --cohort {cohort}")
        native, result = after.get("native", {}), after.get("result_file", {})
        stat = text(self.ssh(f"sudo stat -c '%i %s %Y %a %U' {result.get('path')}", check=True).stdout).strip()
        ok = (reviewed.get("verdict_accepted") is True and reviewed.get("provider_calls") == 1 and status == 0
              and accepted.get("result") == "accepted_and_executed" and accepted.get("human_attestation") is False
              and native.get("program_counter") == "settled_observation_required"
              and native.get("settlement_outcome") == "success"
              and all(native.get("replay", {}).get(k) == 1 for k in ("ag_spends", "docket_attempts", "settlements"))
              and result.get("matches_plan") is True and result.get("scratch_entries") == ["result.txt"])
        return {"ok": ok, "candidate_sha256": candidate, "review": {k: reviewed.get(k) for k in (
            "result", "binding_id", "verdict_accepted", "provider_calls", "grants", "effects")},
                "accept": accepted, "native": {k: v for k, v in native.items() if k != "docket_inspect"},
                "result_file": {k: result.get(k) for k in ("path", "sha256", "bytes", "matches_plan", "scratch_entries")},
                "result_stat": stat}

    def start_fixture(self, which: str) -> dict:
        cohort, port = COHORT[which]
        self.ssh(f"cd {FIXTURE} && (setsid nohup /usr/bin/python3.11 -I {FIXTURE}/fixture-review-tooling/"
                 f"fixture_responses_endpoint.py --port {port} --mode accepted --log {FIXTURE}/{cohort}-requests.jsonl "
                 f"--ready-file {FIXTURE}/{cohort}-ready.json > {FIXTURE}/{cohort}.out 2>&1 &); "
                 f"for i in $(seq 50); do [ -s {FIXTURE}/{cohort}-ready.json ] && break; sleep 0.1; done", check=True)
        ready = json.loads(self.ssh(f"cat {FIXTURE}/{cohort}-ready.json", check=True).stdout)
        if ready.get("bind") != "127.0.0.1":
            raise Refusal(f"fixture is not loopback-only: {ready}")
        return ready

    def b_counts(self) -> dict:
        _, value = self.drv("B", f"status --cohort {COHORT['B'][0]}")
        native = value.get("native", {})
        return {"replay": native.get("replay"), "program_counter": native.get("program_counter"),
                "result_sha256": value.get("result_file", {}).get("sha256"),
                "result_stat": text(self.ssh(f"sudo stat -c '%i %s %Y' {value['result_file']['path']}",
                                             check=True).stdout).strip()}

    # ------------------------------------------------------------ preflight
    def preflight(self) -> None:
        if (self.out / "UPGRADE-CONTINUITY-RESULT.json").exists():
            raise Refusal(f"output already exists: {self.out}")
        for sub in ("cases", "evidence", "qemu"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        self.host_log = (self.out / "host.log").open("a", encoding="utf-8")
        self.identity["harness"] = self.describe_harness()
        self.run_case("P-01", self.case_p01)
        if self.results["P-01"]["outcome"] != "PASS":
            raise Refusal(self.results["P-01"].get("error", "preflight failed"))

    def case_p01(self) -> None:
        import shutil
        for tool in ("qemu-img", "qemu-system-x86_64", "xorriso", "ssh", "ssh-keygen", "scp", "openssl"):
            if shutil.which(tool) is None:
                raise Refusal(f"required tool is absent: {tool}")
        if not os.access("/dev/kvm", os.R_OK | os.W_OK):
            raise Refusal("/dev/kvm is not accessible")
        if not base.port_free(self.args.ssh_port):
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
        if expected is None or actual != expected or os.access(image, os.W_OK):
            raise Refusal("base image is absent from SHA512SUMS, differs, or is writable")
        self.identity["image"] = {"path": str(image), "sha512": actual}
        bundles = {}
        for which, directory in (("A", self.args.bundle_a), ("B", self.args.bundle_b)):
            checked = subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=directory,
                                     capture_output=True, text=True, check=False)
            if checked.returncode != 0:
                raise Refusal(f"bundle {which} SHA256SUMS do not verify: {checked.stdout}{checked.stderr}")
            bundles[which] = {"directory": str(directory), "sha256sums_sha256": file_digest(directory / "SHA256SUMS"),
                              "manifest_sha256": file_digest(directory / "cohort-manifest.json"),
                              "manifest": json.loads((directory / "cohort-manifest.json").read_text())}
        if bundles["A"]["manifest_sha256"] != RUN_003_MANIFEST:
            raise Refusal("bundle A is not run-003's qualified manifest")
        self.identity["host_verifier"] = self.extract_host_verifier(self.args.bundle_a)
        ag = {which: next({k: e[k] for k in AG_PIN} for e in bundles[which]["manifest"]["components"]
                          if e["component"] == "ag") for which in ("A", "B")}
        if ag["A"] != AG_PIN or ag["B"] != AG_PIN:
            raise Refusal(f"both cohorts must carry AG 58122ce: {ag}")
        receipt = json.loads((self.args.docket_build / "build-receipt.v1.json").read_text())
        docket_b = next(e for e in bundles["B"]["manifest"]["components"] if e["component"] == "docket")
        tarball = next(name for name in receipt["artifacts"] if name.endswith(".tar.gz"))
        if (receipt["reproduction"]["byte_equal"] is not True
                or "sha256:" + receipt["artifacts"][tarball]["sha256"] != docket_b["artifact_sha256"]):
            raise Refusal("Docket B is not the byte-equal reproduction the B manifest names")
        differ = sorted(a["component"] for a, b in zip(bundles["A"]["manifest"]["components"],
                                                       bundles["B"]["manifest"]["components"]) if a != b)
        self.identity["bundles"] = bundles
        self.facts["b_construction"] = {"differs_from_a": differ, "docket_b": docket_b,
                                        "docket_b_reproduction": receipt["reproduction"]}
        self.record("PASS" if differ == ["cohort-kit", "docket"] else "FAIL", image_sha512=actual,
                    bundles={k: {x: v[x] for x in ("sha256sums_sha256", "manifest_sha256")} for k, v in bundles.items()},
                    b_differs_from_a=differ, ag_in_both=ag["A"], host_verifier=self.identity["host_verifier"])

    # ------------------------------------------------------------ guest
    def case_i01(self) -> None:
        guest = self.prepare_guest()
        guest.name = "g3-upgrade-continuity"
        self.start_guest(guest)
        self.wait_ssh(guest)
        self.ssh("cloud-init status --wait >/dev/null; cloud-init status", timeout=900)
        release = self.ssh('. /etc/os-release; printf "%s:%s" "$ID" "$VERSION_ID"', check=True).stdout
        if release != b"debian:12":
            raise Refusal(f"not Debian 12: {release!r}")
        self.ssh(f"mkdir -p {GH}/bin {FIXTURE} {KIT['A']} {KIT['B']} {BUNDLE['A']}/qualification-only "
                 f"{BUNDLE['B']}/qualification-only && sudo install -d -m 0700 {WORK}", check=True)
        self.scp_to([HERE / "guest" / "g3_guest.py"], f"{GH}/bin/")
        kits = {}
        for which, directory in (("A", self.args.bundle_a), ("B", self.args.bundle_b)):
            self.scp_to(sorted(p for p in directory.iterdir() if p.is_file()), f"{BUNDLE[which]}/")
            self.scp_to(sorted((directory / "qualification-only").iterdir()), f"{BUNDLE[which]}/qualification-only/")
            self.ssh(f"cd {BUNDLE[which]} && sha256sum --check --strict SHA256SUMS", check=True)
            [kit] = [p.name for p in directory.iterdir() if p.name.startswith("cohort-kit-")]
            self.ssh(f"tar -xzf {BUNDLE[which]}/{kit} -C {KIT[which]} --no-same-owner", check=True)
            top = kit.removesuffix(".tar.gz")
            self.facts[f"kit_{which}"] = f"{KIT[which]}/{top}"
            self.facts[f"driver_{which}"] = f"{PY} {KIT[which]}/{top}/setup/constellation_cohort.py"
            kits[which] = text(self.ssh(f"{self.facts['driver_' + which]} --version", check=True).stdout).strip()
        fixture = sorted((self.args.bundle_a / "qualification-only").iterdir())[0].name
        self.ssh(f"tar -xzf {BUNDLE['A']}/qualification-only/{fixture} -C {FIXTURE} --no-same-owner", check=True)
        self.record("PASS", os=release.decode(), drivers=kits)

    def case_i02(self) -> None:
        results = {}
        for which in ("A", "B"):
            done = self.ssh(f"{PY} -B {self.facts['kit_' + which]}/setup/test_constellation_cohort.py -v 2>&1")
            results[which] = {"exit": done.returncode, "tail": text(done.stdout).strip().splitlines()[-3:]}
        ok = all(r["exit"] == 0 and any(line.startswith("OK") for line in r["tail"]) for r in results.values())
        self.record("PASS" if ok else "FAIL", tests=results)

    # ------------------------------------------------------------ cohort A
    def case_a01(self) -> None:
        cohort, port = COHORT["A"]
        status_v, verify = self.drv("A", f"verify-manifest --manifest {BUNDLE['A']}/cohort-manifest.json "
                                         f"--artifacts {BUNDLE['A']}")
        status_i, install = self.drv("A", f"install --cohort {cohort} --manifest {BUNDLE['A']}/cohort-manifest.json "
                                          f"--artifacts {BUNDLE['A']}")
        status_n, init = self.drv("A", f"init --cohort {cohort} --review-route fixture-review --fixture-port {port}")
        if not (status_v == status_i == status_n == 0):
            raise Refusal(f"A setup refused: {verify} {install} {init}")
        flow = self.workflow("A")
        self.facts["a_workflow"] = flow
        ok = verify.get("qualified_cohort") == "alpha-exit-rc" and flow.pop("ok")
        self.record("PASS" if ok else "FAIL", qualified_cohort=verify.get("qualified_cohort"),
                    init={k: init.get(k) for k in ("binding_id", "occurrence")}, **flow)

    def case_a02(self) -> None:
        self.passed("A-01")
        status, value = self.drv("A", f"evidence --cohort {COHORT['A'][0]} --output {EXPORT['A']}")
        target = self.pull(EXPORT["A"], "a-evidence-pre-upgrade")
        code, verified = self.host_verify(target, "a-pre-upgrade")
        sums = "sha256:" + file_digest(target / "SHA256SUMS")
        self.facts["a_export_sha256sums"] = sums
        self.facts["a_export_files"] = value.get("files")
        ok = status == 0 and value.get("join_complete") is True and code == 0 and verified.get("result") == "passed"
        self.record("PASS" if ok else "FAIL", evidence=value, host_verifier=verified, export_sha256sums=sums)

    # ------------------------------------------------------------ pins
    def variant(self, which: str, name: str, replace_with: str, component: str) -> str:
        """Bundle `which`'s manifest with one component entry taken from the other bundle."""
        path = f"{GH}/{name}.json"
        code = ("import json,sys; m=json.load(open(sys.argv[1])); o=json.load(open(sys.argv[2])); "
                "e=[x for x in o['components'] if x['component']==sys.argv[3]][0]; "
                "m['components']=[e if x['component']==sys.argv[3] else x for x in m['components']]; "
                "open(sys.argv[4],'w').write(json.dumps(m))")
        self.ssh(f"{PY} -c {shlex.quote(code)} {BUNDLE[which]}/cohort-manifest.json "
                 f"{BUNDLE[replace_with]}/cohort-manifest.json {component} {path}", check=True)
        return path

    def case_m01(self) -> None:
        self.passed("A-01")
        before = self.snapshot()
        trials = {
            "B driver, A manifest": ("B", f"{BUNDLE['A']}/cohort-manifest.json", BUNDLE["A"]),
            "B driver, B manifest with A's docket": ("B", self.variant("B", "m-b-with-a-docket", "A", "docket"), BUNDLE["B"]),
            "A driver, B manifest": ("A", f"{BUNDLE['B']}/cohort-manifest.json", BUNDLE["B"]),
            "A driver, A manifest with B's docket": ("A", self.variant("A", "m-a-with-b-docket", "B", "docket"), BUNDLE["A"]),
        }
        observed, ok = {}, True
        for label, (which, manifest, artifacts) in trials.items():
            status_v, verify = self.drv(which, f"verify-manifest --manifest {manifest} --artifacts {artifacts}")
            status_i, install = self.drv(which, f"install --cohort g3-mixed --manifest {manifest} --artifacts {artifacts}")
            observed[label] = {"verify": verify, "install": install}
            ok &= (status_v == 2 and verify.get("code") == "pin.incompatible" and status_i == 2
                   and install.get("code") == "pin.incompatible")
        after = self.snapshot()
        self.record("PASS" if ok and before == after else "FAIL", trials=observed, writes_unchanged=before == after)

    # ------------------------------------------------------------ cohort B install
    def case_b01(self) -> None:
        self.passed("A-01")
        cohort = COHORT["B"][0]
        a_record = text(self.ssh(f"sudo sha256sum /opt/constellation/cohorts/{COHORT['A'][0]}/installed.json",
                                 check=True).stdout).split()[0]
        status_v, verify = self.drv("B", f"verify-manifest --manifest {BUNDLE['B']}/cohort-manifest.json "
                                         f"--artifacts {BUNDLE['B']}")
        status_i, install = self.drv("B", f"install --cohort {cohort} --manifest {BUNDLE['B']}/cohort-manifest.json "
                                          f"--artifacts {BUNDLE['B']}")
        record = self.root_json(f"cat /opt/constellation/cohorts/{cohort}/installed.json")
        docket = {p: v for p, v in record["identities"].items() if f"/cohorts/{cohort}/docket/" in p}
        a_after = text(self.ssh(f"sudo sha256sum /opt/constellation/cohorts/{COHORT['A'][0]}/installed.json",
                                check=True).stdout).split()[0]
        ok = (status_v == 0 and verify.get("qualified_cohort") == "g3-qual-b" and status_i == 0
              and all(v["version"] == "0.1.1-qual.g3b" for v in docket.values()) and len(docket) == 2
              and a_record == a_after)
        self.record("PASS" if ok else "FAIL", verify=verify, install=install, docket_identities=docket,
                    a_install_record_unchanged=a_record == a_after)

    # ------------------------------------------------------------ upgrade
    def upgrade_args(self, extra: str = "", export: str | None = None) -> str:
        return (f"upgrade --from-cohort {COHORT['A'][0]} --to-cohort {COHORT['B'][0]} "
                f"--export {export or EXPORT['A']}{extra}")

    def case_u01(self) -> None:
        self.passed("A-02", "B-01")
        self.ssh(f"sudo sh -c 'cp -a {EXPORT['A']} {WORK}/u01-flip && chmod u+w {WORK}/u01-flip/native/ag-inspect.json && "
                 f"printf \" \" >> {WORK}/u01-flip/native/ag-inspect.json && cp -a {EXPORT['A']} {WORK}/u01-pad && "
                 f"echo extra > {WORK}/u01-pad/native/extra.json'", check=True)
        mid = self.snapshot()
        s1, flipped = self.drv("B", self.upgrade_args(export=f"{WORK}/u01-flip"))
        s2, padded = self.drv("B", self.upgrade_args(export=f"{WORK}/u01-pad"))
        after = self.snapshot()
        journal = self.ssh(f"sudo test -e {JOURNAL}").returncode == 0
        ok = (s1 == 2 and flipped.get("code") == "export.digest_mismatch" and s2 == 2
              and padded.get("code") == "export.unlisted" and mid == after and not journal)
        self.record("PASS" if ok else "FAIL", flipped=flipped, padded=padded, writes_unchanged=mid == after,
                    journal_created=journal, note="the tampered copies are harness scratch under /root/g3")

    def case_u02(self) -> None:
        self.passed("A-02", "B-01")
        driver_path = self.facts["driver_B"].split()[-1]
        done = self.ssh(f"sudo {PY} {HELPER} interrupt --driver {driver_path} --journal {JOURNAL} "
                        f"--step retain.started --glob '/var/lib/constellation/retained/{COHORT['A'][0]}/.partial-*/records' "
                        f"-- {self.upgrade_args()}", timeout=900)
        report = json.loads(done.stdout)
        _, status = self.drv("B", "upgrade-status")
        s_init, init = self.drv("B", f"init --cohort {COHORT['B'][0]} --review-route fixture-review "
                                     f"--fixture-port {COHORT['B'][1]}")
        b_state = self.ssh(f"sudo test -e {STATE}/{COHORT['B'][0]}").returncode == 0
        s_rerun, rerun = self.drv("B", self.upgrade_args())
        s_ver, verify = self.drv("B", f"verify-retained --cohort {COHORT['A'][0]}")
        export_intact = self.ssh(f"sudo sh -c 'cd {EXPORT['A']} && sha256sum --check --strict --quiet SHA256SUMS'"
                                 ).returncode == 0
        a_state = text(self.ssh(f"sudo sh -c 'for d in {STATE}/{COHORT['A'][0]} /var/lib/constellation/quarantine/"
                                f"{COHORT['A'][0]}/state; do test -d $d && ls $d/deployment/ag.sqlite "
                                f"$d/ports/docket-state/state.sqlite $d/ports/issuer.pk8 $d/scratch/result.txt; done'",
                                check=False).stdout).split()
        retained = text(self.ssh(f"sudo ls -a /var/lib/constellation/retained/{COHORT['A'][0]} 2>/dev/null").stdout).split()
        self.facts["interrupt"] = report
        partial = [name for name in retained if name.startswith(".partial-")]
        ok = ((report.get("killed_after") or "").startswith(f"{JOURNAL}/attempt-001/retain.started.json + ")
              and partial == [".partial-g3-a-to-g3-b-attempt-001"]
              and report.get("returncode") == -9
              and any(j["interrupted"] == ["attempt-001"] for j in status.get("journals", []))
              and s_init == 2 and init.get("code") == "upgrade.interrupted" and not b_state
              and s_rerun == 2 and rerun.get("code") == "upgrade.interrupted"
              and s_ver == 2 and verify.get("code") == "retained.not_recorded"
              and export_intact and len(a_state) == 4
              and not any(name.startswith("sha256-") for name in retained))
        self.record("PASS" if ok else "FAIL", interrupt=report, upgrade_status=status, successor_init=init,
                    plain_rerun=rerun, verify_retained=verify, export_intact=export_intact,
                    a_state_files=a_state, retained_dir=retained)

    def case_u03(self) -> None:
        self.passed("U-02")
        status, value = self.drv("B", self.upgrade_args(" --after-interrupted attempt-001"))
        a = COHORT["A"][0]
        tomb = self.optional_json(f"{STATE}/{a}")
        layout = text(self.ssh(f"sudo sh -c 'ls -la {STATE}; ls /var/lib/constellation/quarantine/{a}/state; "
                               f"ls -la /var/lib/nq/quarantine-cohort-{a}; ls /etc/nq; ls -a /var/lib/constellation/retained/{a}'",
                               check=True).stdout)
        present = {path: self.ssh(f"sudo test -e {path}").returncode == 0 for path in (
            f"/etc/nq/cohort-{a}.toml", f"/var/lib/nq/cohort-{a}", f"/var/lib/nq/quarantine-cohort-{a}/cohort-{a}.toml",
            f"/var/lib/nq/quarantine-cohort-{a}/store/nq.db", f"/var/lib/constellation/quarantine/{a}/state/ports/issuer.pk8",
            f"/var/lib/constellation/quarantine/{a}/state/deployment/ag.sqlite",
            f"/var/lib/constellation/retained/{a}/.partial-g3-a-to-g3-b-attempt-001")}
        expected_present = {path: not path.startswith((f"/etc/nq/cohort-{a}", f"/var/lib/nq/cohort-{a}")) for path in present}
        _, st = self.drv("B", "upgrade-status")
        self.facts["upgrade"] = value
        checks = value.get("checks", {})
        ok = (status == 0 and value.get("result") == "upgraded"
              and all(checks.get("export", {}).values()) and all(checks.get("retained", {}).values())
              and set(checks.get("export", {})) == {"docket_reinspection", "issuance_identity", "issuance_signature",
                                                     "ag_reinspection"}
              and value.get("retained_sha256sums") == self.facts.get("a_export_sha256sums")
              and (tomb or {}).get("schema") == "constellation.cohort-retired/v1" and present == expected_present)
        self.record("PASS" if ok else "FAIL", upgrade=value, tombstone=tomb, paths_present=present, layout=layout,
                    upgrade_status=st)

    def case_u04(self) -> None:
        self.passed("U-03")
        status, value = self.drv("B", f"verify-retained --cohort {COHORT['A'][0]}")
        retained = value.get("retained") or self.facts["upgrade"]["retained"]
        target = self.pull(retained, "a-retained-under-b")
        code, verified = self.host_verify(target, "a-retained")
        pre = self.out / "evidence" / "a-evidence-pre-upgrade"
        pre_files = sorted(str(p.relative_to(pre)) for p in pre.rglob("*") if p.is_file())
        differing = [name for name in pre_files if (target / name).read_bytes() != (pre / name).read_bytes()]
        extra = sorted(str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()
                       and not (pre / p.relative_to(target)).exists())
        ok = (status == 0 and value.get("result") == "retained_verified" and all(value.get("checks", {}).values())
              and value.get("sha256sums") == self.facts["a_export_sha256sums"] and code == 0
              and verified.get("result") == "passed" and not differing and extra == ["RETAINED.json"]
              and verified.get("sha256sums_sha256") == self.facts["a_export_sha256sums"])
        self.record("PASS" if ok else "FAIL", verify_retained=value, host_verifier=verified,
                    files_compared=len(pre_files), differing=differing, extra_in_retained=extra)

    # ------------------------------------------------------------ cohort B
    def case_b02(self) -> None:
        self.passed("U-03")
        cohort, port = COHORT["B"]
        status, init = self.drv("B", f"init --cohort {cohort} --review-route fixture-review --fixture-port {port}")
        pre = self.out / "evidence" / "a-evidence-pre-upgrade"
        a_ids = json.loads((pre / "records/driver/identities.json").read_text())
        a_trust = json.loads((pre / "state/ports/docket-trust.json").read_text())["issuers"]
        b_ids = self.root_json(f"cat {STATE}/{cohort}/driver/identities.json")
        b_trust = self.root_json(f"cat {STATE}/{cohort}/ports/docket-trust.json")["issuers"]
        keys = ("operator", "issuer_principal", "issuer_key_id", "standing_resolver_id", "author_principal",
                "occurrence", "campaign", "program", "subject", "nq_subject", "run_id", "adapter_process", "draft_id")
        table = {key: {"A": a_ids.get(key), "B": b_ids.get(key), "same": a_ids.get(key) == b_ids.get(key)} for key in keys}
        table["reviewer_id"] = {"A": a_ids.get("reviewer_id"), "B": b_ids.get("reviewer_id"),
                                "same": a_ids.get("reviewer_id") == b_ids.get("reviewer_id")}
        table["issuer_public_key"] = {"A": a_trust[0]["public_key"], "B": b_trust[0]["public_key"],
                                      "same": a_trust == b_trust}
        self.facts["identity_table"] = table
        fresh = all(not row["same"] for key, row in table.items() if key != "reviewer_id")
        ok = (status == 0 and init.get("result") == "initialized"
              and (init.get("predecessor") or {}).get("from") == COHORT["A"][0]
              and (init.get("predecessor") or {}).get("retained_sha256sums") == self.facts["a_export_sha256sums"]
              and fresh and len(a_trust) == len(b_trust) == 1)
        self.record("PASS" if ok else "FAIL", init=init, identities=table,
                    note="reviewer_id is the fixture route's fixed label in both cohorts, by design")

    def case_b03(self) -> None:
        self.passed("B-02")
        flow = self.workflow("B")
        self.facts["b_workflow"] = flow
        status, value = self.drv("B", f"evidence --cohort {COHORT['B'][0]} --output {EXPORT['B']}")
        target = self.pull(EXPORT["B"], "b-evidence")
        code, verified = self.host_verify(target, "b")
        ok = flow.pop("ok") and status == 0 and value.get("join_complete") is True and code == 0 \
            and verified.get("result") == "passed"
        self.record("PASS" if ok else "FAIL", **flow, evidence=value, host_verifier=verified)

    # ------------------------------------------------------------ no effect from A under B
    def a_retained(self) -> str:
        return self.facts["upgrade"]["retained"]

    def present(self, argv: str) -> dict:
        done = self.ssh(f"sudo {PY} {HELPER} present-issuance --kit-setup {self.facts['kit_B']}/setup "
                        f"--retained {self.a_retained()} -- {argv}", check=True)
        return json.loads(done.stdout)

    def b_accept_argv(self, state: str, trust: str) -> str:
        b = f"{STATE}/{COHORT['B'][0]}"
        docket = self.installed_program("B", "docket", "bin/docket")
        executor = self.installed_program("B", "maude", "lib/executor.pyz")
        return (f"{docket} governed-loop accept --state {state} --trust {trust} "
                f"--standing-resolver {b}/ports/docket-standing-launcher --executor {executor} "
                f"--executor-config {b}/plan/executor-config.json")

    def a_issuance(self) -> str:
        pre = self.out / "evidence" / "a-evidence-pre-upgrade"
        return json.loads((pre / "native/docket-inspect.json").read_text())["requested_issuance"]

    def case_x01(self) -> None:
        self.passed("B-03")
        b = f"{STATE}/{COHORT['B'][0]}"
        before = self.b_counts()
        presented = self.present(self.b_accept_argv(f"{b}/ports/docket-state", f"{b}/ports/docket-trust.json")
                                 + " --require-local-standing-snapshot")
        docket = self.installed_program("B", "docket", "bin/docket")
        looked = self.ssh(f"sudo setpriv --reuid=constellation --regid=constellation --init-groups {docket} "
                          f"governed-loop inspect --state {b}/ports/docket-state --issuance {self.a_issuance()}")
        try:
            inspect = json.loads(looked.stdout) if looked.returncode == 0 else {"exit": looked.returncode}
        except ValueError:
            inspect = {"unparsed": text(looked.stdout)[-400:]}
        after = self.b_counts()
        ok = presented["exit"] != 0 and looked.returncode == 0 and inspect.get("record") is None and before == after
        self.record("PASS" if ok else "FAIL", presented=presented, b_docket_record_for_a_issuance=inspect.get("record"),
                    b_before=before, b_after=after)

    def scratch_docket(self, name: str, *, from_retained: bool) -> str:
        """A constellation-owned scratch Docket state (a copy of A's retained store, or empty)."""
        path = f"/var/lib/constellation/{name}"
        copy = f"cp {self.a_retained()}/stores/docket.sqlite {path}/docket-state/state.sqlite && " if from_retained else ""
        self.ssh(f"sudo sh -c 'install -d -o constellation -g constellation -m 0700 {path} {path}/docket-state && {copy}"
                 f"cp {self.a_retained()}/state/ports/docket-trust.json {path}/a-trust.json && "
                 f"chown -R constellation:constellation {path} && chmod -R u+rwX {path}'", check=True)
        return path

    def case_x02(self) -> None:
        self.passed("B-03", "U-03")
        path = self.scratch_docket("g3-x02", from_retained=True)
        docket = self.installed_program("B", "docket", "bin/docket")
        read = (f"setpriv --reuid=constellation --regid=constellation --init-groups {docket} governed-loop inspect "
                f"--state {path}/docket-state --issuance {self.a_issuance()}")
        before = self.root_json(read)
        b_before = self.b_counts()
        presented = self.present(self.b_accept_argv(f"{path}/docket-state", f"{path}/a-trust.json"))
        after = self.root_json(read)
        b_after = self.b_counts()
        a_custody = before.get("record", {}).get("custody")
        returned = json.loads(presented["stdout"]) if presented["exit"] == 0 and presented["stdout"].strip() else None
        ok = (after == before and (before.get("record") or {}).get("status") == "settled" and b_before == b_after
              and (presented["exit"] != 0 or returned == a_custody))
        self.record("PASS" if ok else "FAIL", presented=presented, returned_custody_equals_a=returned == a_custody,
                    record_unchanged=after == before, b_unchanged=b_before == b_after,
                    note="a copy of A's retained Docket store; the retained store itself is read-only")

    def case_x03(self) -> None:
        self.passed("B-03", "U-03")
        path = self.scratch_docket("g3-x03", from_retained=False)
        b_before = self.b_counts()
        presented = self.present(self.b_accept_argv(f"{path}/docket-state", f"{path}/a-trust.json"))
        docket = self.installed_program("B", "docket", "bin/docket")
        records = self.ssh(f"sudo setpriv --reuid=constellation --regid=constellation --init-groups {docket} "
                           f"governed-loop inspect --state {path}/docket-state --issuance {self.a_issuance()}")
        b_after = self.b_counts()
        expired = "governed-issuance-expired" in presented["stdout"] + presented["stderr"]
        ok = (presented["exit"] != 0 and expired and presented["presented_at_unix_ms"] >= presented["not_after_unix_ms"]
              and b_before == b_after)
        self.record("PASS" if ok else "FAIL", presented=presented, refused_as_expired=expired,
                    inspect_after=text(records.stdout)[-800:] + text(records.stderr)[-400:], b_unchanged=b_before == b_after)

    def case_x04(self) -> None:
        self.passed("B-03", "U-03")
        pre = self.out / "evidence" / "a-evidence-pre-upgrade"
        issuance = json.loads((pre / "native/docket-inspect.json").read_text())["record"]["issuance"]
        a_ids = json.loads((pre / "records/driver/identities.json").read_text())
        b = f"{STATE}/{COHORT['B'][0]}"
        b_ids = self.root_json(f"cat {b}/driver/identities.json")
        docket = self.installed_program("B", "docket", "bin/docket")
        as_c = "setpriv --reuid=constellation --regid=constellation --init-groups"
        snapshot = self.ssh(f"sudo {as_c} {docket} governed-loop standing-snapshot --state {b}/ports/docket-state "
                            f"--issuance {issuance['issuance']}")
        now = int(time.time() * 1000)

        def grant(state: str, operator: str, tuple_: dict) -> subprocess.CompletedProcess:
            return self.ssh(f"sudo {as_c} {docket} governed-loop standing-grant --state {state} --operator {operator} "
                            f"--campaign {tuple_['campaign']} --occurrence {tuple_['occurrence']} "
                            f"--program {tuple_['program']} --work-schema {tuple_['work_schema']} --work {tuple_['work']} "
                            f"--subject {tuple_['subject']} --scope {tuple_['scope']} --issued-at-unix-ms {now} "
                            f"--expires-at-unix-ms {now + 60000}")
        a_tuple = {**issuance["key"], **{k: issuance[k] for k in ("program", "work_schema", "work", "subject", "scope")}}
        path = self.scratch_docket("g3-x04", from_retained=True)
        b_in_a = grant(f"{path}/docket-state", b_ids["operator"], a_tuple)
        b_copy = "/var/lib/constellation/g3-x04b"
        self.ssh(f"sudo sh -c 'install -d -o constellation -g constellation -m 0700 {b_copy} && "
                 f"cp -a {b}/ports/docket-state {b_copy}/docket-state'", check=True)
        a_in_b = grant(f"{b_copy}/docket-state", a_ids["operator"], a_tuple)
        b_trust = self.root_json(f"cat {b}/ports/docket-trust.json")["issuers"]
        a_trust = json.loads((pre / "state/ports/docket-trust.json").read_text())["issuers"]
        mismatch = "operator-enrollment-mismatch"
        no_snapshot = snapshot.returncode != 0 or text(snapshot.stdout).strip() == "null"
        ok = (no_snapshot and b_in_a.returncode != 0 and mismatch in text(b_in_a.stdout + b_in_a.stderr)
              and a_in_b.returncode != 0 and mismatch in text(a_in_b.stdout + a_in_b.stderr)
              and not any(entry in b_trust for entry in a_trust))
        self.record("PASS" if ok else "FAIL",
                    b_snapshot_of_a_issuance={"exit": snapshot.returncode,
                                              "output": text(snapshot.stdout + snapshot.stderr)[-600:]},
                    b_operator_grant_in_a_state={"exit": b_in_a.returncode, "output": text(b_in_a.stdout + b_in_a.stderr)[-600:]},
                    a_operator_grant_in_b_state_copy={"exit": a_in_b.returncode,
                                                      "output": text(a_in_b.stdout + a_in_b.stderr)[-600:]},
                    a_key_in_b_trust=any(entry in b_trust for entry in a_trust))

    def case_x05(self) -> None:
        self.passed("B-03", "U-03")
        b = f"{STATE}/{COHORT['B'][0]}"
        ag = self.installed_program("B", "ag", "bin/ag-loopctl")
        as_c = "setpriv --reuid=constellation --regid=constellation --init-groups"
        run_input = f"{self.a_retained()}/caller/continuation-001/run-input-v2.json"
        exists = self.ssh(f"sudo test -f {run_input}").returncode == 0
        before = self.root_json(f"{as_c} {ag} inspect --database {b}/deployment/ag.sqlite")
        self.ssh(f"sudo sh -c 'cp {run_input} /var/lib/constellation/g3-x05-run-input.json && "
                 f"chown constellation /var/lib/constellation/g3-x05-run-input.json'", check=True)
        done = self.ssh(f"sudo {as_c} {ag} run --database {b}/deployment/ag.sqlite "
                        f"--run-input /var/lib/constellation/g3-x05-run-input.json", timeout=300)
        after = self.root_json(f"{as_c} {ag} inspect --database {b}/deployment/ag.sqlite")
        b_counts = self.b_counts()
        ok = (exists and done.returncode != 0 and before == after
              and all((b_counts["replay"] or {}).get(k) == 1 for k in ("ag_spends", "docket_attempts", "settlements")))
        self.record("PASS" if ok else "FAIL", run_input_retained=exists, exit=done.returncode,
                    output=text(done.stdout + done.stderr)[-1200:], b_ag_unchanged=before == after,
                    b_state_digest=after["current"].get("state_digest"))

    def case_x06(self) -> None:
        self.passed("U-03")
        a, port = COHORT["A"][0], 18463
        before = self.snapshot()
        s1, b_init = self.drv("B", f"init --cohort {a} --review-route fixture-review --fixture-port {port}")
        s2, a_init = self.drv("A", f"init --cohort {a} --review-route fixture-review --fixture-port {port}")
        s3, a_review = self.drv("A", f"review --cohort {a}")
        s4, a_status = self.drv("A", f"status --cohort {a}")
        after = self.snapshot()
        # A's kit is 0.3.0 too, so its init names the retirement before the
        # tombstone (the pre-0.3.0 tombstone path was run-001's X-06).
        ok = (s1 == 2 and b_init.get("code") == "cohort.retired" and s2 == 2
              and a_init.get("code") == "cohort.retired"
              and s3 == 2 and a_review.get("code") == "cohort.not_initialized" and a_status.get("initialized") is False
              and before == after)
        self.record("PASS" if ok else "FAIL", b_driver_init=b_init, a_driver_init=a_init, a_driver_review=a_review,
                    a_driver_status=a_status, writes_unchanged=before == after)

    # ------------------------------------------------------------ tamper
    def case_t01(self) -> None:
        self.passed("U-04")
        copy = f"{WORK}/t01-retained"
        self.ssh(f"sudo sh -c 'cp -a {self.a_retained()} {copy} && chmod -R u+w {copy} && "
                 f"printf \" \" >> {copy}/native/docket-inspect.json'", check=True)
        status, value = self.drv("B", f"verify-retained --cohort {COHORT['A'][0]} --retained {copy}")
        target = self.pull(copy, "t01-tampered-retained")
        code, verified = self.host_verify(target, "t01-tampered")
        s2, genuine = self.drv("B", f"verify-retained --cohort {COHORT['A'][0]}")
        ok = (status == 2 and value.get("code") == "retained.digest_mismatch" and code != 0
              and "native/docket-inspect.json" in verified.get("digest_mismatches", [])
              and s2 == 0 and genuine.get("result") == "retained_verified")
        self.record("PASS" if ok else "FAIL", verify_retained=value, host_verifier=verified,
                    genuine_still_verifies=genuine.get("result"))

    def case_t02(self) -> None:
        self.passed("U-04")
        copy = f"{WORK}/t02-retained"
        code = ("import hashlib,json,pathlib,sys; r=pathlib.Path(sys.argv[1]); p=r/'stores/docket.sqlite'; "
                "b=bytearray(p.read_bytes()); b[-1]^=1; p.write_bytes(bytes(b)); "
                "lines=[l for l in (r/'SHA256SUMS').read_text().splitlines()]; "
                "out=''.join((hashlib.sha256((r/n).read_bytes()).hexdigest()+'  '+n+'\\n') for n in [l.split('  ',1)[1] for l in lines]); "
                "(r/'SHA256SUMS').write_text(out); m=json.loads((r/'RETAINED.json').read_text()); "
                "m['sha256sums']='sha256:'+hashlib.sha256(out.encode()).hexdigest(); (r/'RETAINED.json').write_text(json.dumps(m))")
        self.ssh(f"sudo sh -c 'cp -a {self.a_retained()} {copy} && chmod -R u+w {copy}' && "
                 f"sudo {PY} -c {shlex.quote(code)} {copy}", check=True)
        status, value = self.drv("B", f"verify-retained --cohort {COHORT['A'][0]} --retained {copy}")
        ok = status == 2 and value.get("code") == "retained.not_recorded"
        self.record("PASS" if ok else "FAIL", verify_retained=value)

    # ------------------------------------------------------------ AG key probe
    def case_k01(self) -> None:
        self.passed("U-03")
        a = COHORT["A"][0]
        quarantined = f"/var/lib/constellation/quarantine/{a}/state"
        ag = self.installed_program("B", "ag", "bin/ag-loopctl")
        common = (f"sudo {PY} {HELPER} ag-view --kit-setup {self.facts['kit_B']}/setup --cohort {a} --ag {ag} "
                  f"--database {self.a_retained()}/stores/ag.sqlite")
        view = {
            "quarantine_with_key": json.loads(self.ssh(f"{common} --state {quarantined}", check=True).stdout),
            "quarantine_without_key": json.loads(self.ssh(f"{common} --state {quarantined} --without ports/issuer.pk8",
                                                          check=True).stdout),
            "quarantine_garbage_key": json.loads(self.ssh(f"{common} --state {quarantined} --garbage ports/issuer.pk8",
                                                          check=True).stdout),
            # A's retained evidence alone: no quarantine, no key, no launchers.
            "retained_state_only": json.loads(self.ssh(f"{common} --state {self.a_retained()}/state --own",
                                                       check=True).stdout),
        }
        pre = self.out / "evidence" / "a-evidence-pre-upgrade"
        expected = json.loads((pre / "native/ag-inspect.json").read_text())["current"]["state_digest"]
        control = view["quarantine_with_key"]
        keyless = all(view[name]["exit"] == 0 and view[name]["outcome"] == "verified"
                      and view[name]["state_digest"] == expected and view[name]["stdout_sha256"] == control["stdout_sha256"]
                      for name in ("quarantine_with_key", "quarantine_without_key", "quarantine_garbage_key"))
        retained = view["retained_state_only"]
        named = sorted(entry["path"] for entry in retained["unavailable"] or [])
        retained_ok = (retained["exit"] == 3 and retained["outcome"] == "verified_except_unavailable"
                       and retained["state_digest"] == expected and bool(named)
                       and all(path.startswith(f"{STATE}/{a}/") for path in named))
        # The driver path with the retired key set aside (operator S-2 is
        # undecided, so the harness puts the key back afterwards).
        key, aside = f"{quarantined}/ports/issuer.pk8", f"{WORK}/k01-issuer.pk8.aside"
        self.ssh(f"sudo mv {key} {aside}", check=True)
        try:
            status, verified = self.drv("B", f"verify-retained --cohort {a}")
        finally:
            self.ssh(f"sudo mv {aside} {key}", check=True)
        restored = self.ssh(f"sudo test -f {key}").returncode == 0
        driver_ok = (status == 0 and verified.get("result") == "retained_verified"
                     and verified.get("checks", {}).get("ag_reinspection") is True
                     and verified.get("observed", {}).get("ag", {}).get("outcome") == "verified")
        self.facts["k01"] = view
        self.record("PASS" if keyless and retained_ok and driver_ok and restored else "FAIL",
                    expected_state_digest=expected, views=view, keyless_identical=keyless,
                    retained_state_only_exit3=retained_ok, retained_state_only_named=named,
                    verify_retained_without_key=verified, key_put_back=restored,
                    finding=("AG replays A's retained store without A's issuer private key (D-1 fixed); from the "
                             "retained evidence alone it verifies all but the named launchers and exits 3, which is "
                             "never success") if keyless and retained_ok and driver_ok else None)

    # ------------------------------------------------------------ main
    def execute_all(self) -> None:
        self.run_case("I-01", self.case_i01)
        if self.results["I-01"]["outcome"] != "PASS":
            raise Refusal("guest did not boot")
        for cid, function in (("I-02", self.case_i02), ("A-01", self.case_a01), ("A-02", self.case_a02),
                              ("M-01", self.case_m01), ("B-01", self.case_b01), ("U-01", self.case_u01),
                              ("U-02", self.case_u02), ("U-03", self.case_u03), ("U-04", self.case_u04),
                              ("B-02", self.case_b02), ("B-03", self.case_b03), ("X-01", self.case_x01),
                              ("X-02", self.case_x02), ("X-03", self.case_x03), ("X-04", self.case_x04),
                              ("X-05", self.case_x05), ("X-06", self.case_x06), ("T-01", self.case_t01),
                              ("T-02", self.case_t02), ("K-01", self.case_k01)):
            self.run_case(cid, function)
        self.ssh("pkill -f fixture_responses_endpoint.py || true")

    def destroy(self) -> None:
        super().destroy()
        leftover = subprocess.run(["pgrep", "-f", "process=g3-upgrade-continuity"], capture_output=True, text=True)
        self.facts["qemu_left_running"] = leftover.stdout.split()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bundle-a", type=pathlib.Path, required=True, help="the qualified alpha-exit-rc bundle (run-002)")
    p.add_argument("--bundle-b", type=pathlib.Path, required=True, help="compose_cohort_b.py output")
    p.add_argument("--docket-build", type=pathlib.Path, required=True, help="Docket B build_release.py output")
    p.add_argument("--output-root", type=pathlib.Path, default=DEFAULT_OUTPUT_ROOT)
    p.add_argument("--output-name", required=True, help="run-NNN")
    p.add_argument("--state-dir", type=pathlib.Path, default=DEFAULT_STATE)
    p.add_argument("--image", type=pathlib.Path, default=base.DEFAULT_IMAGE)
    p.add_argument("--ssh-port", type=int, default=23461, help="G3 lane range 23461-23469")
    p.add_argument("--vcpus", type=int, default=2)
    p.add_argument("--memory-mib", type=int, default=4096)
    p.add_argument("--keep-guest", action="store_true", help="debugging only: leave the guest running")
    return p


if __name__ == "__main__":
    sys.exit(Harness(parser().parse_args()).main())
