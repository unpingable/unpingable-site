"""Fixture-scoped qualification for the read-only objective occurrence wrapper."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
PATH = ROOT / "constellation/examples/capture_objective_occurrence.py"
SPEC = importlib.util.spec_from_file_location("capture_objective_occurrence", PATH)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)
AG_ROOT = Path("/data/git/constellation/constellation-ag")
AG_REVISION = "31fde40df33d4e454a660cb27442b60f16054a65"


def source(value=None, *, unavailable=False):
    if unavailable:
        return {"availability": "unavailable", "error_kind": "fixture_refusal"}
    return {"availability": "available", "value": value or {}}


def fixture():
    expected = {
        "plan_digest": "sha256:" + "a" * 64,
        "campaign_id": "sha256:" + "b" * 64,
        "occurrence_id": "00000000-0000-0000-0000-000000000001",
        "proposal_id": "sha256:" + "c" * 64,
        "exact_work_id": "sha256:" + "d" * 64,
        "issuance_id": "sha256:" + "e" * 64,
    }
    detail = {
        "schema": "ag.operator-ui.campaign-detail/v1",
        "inspect": source(), "status": source(), "replay": source(), "history": source(),
        "refusals": source(unavailable=True),
        "projection": {"correspondence": "exact"},
        "docket": [{"result": source({"requested_issuance": expected["issuance_id"],
                                       "record": {"status": "indeterminate"}})}],
    }
    return expected, {
        "schema": "phosphor-ng.objective-detail/v2",
        "objective": {"availability": "available", "plan_digest": expected["plan_digest"]},
        "conditions": [{"disposition": "indeterminate", "evidence": [{"source_currentness": "stale"}]}],
        "occurrences": [{**expected, "maude_plan_ref": expected["plan_digest"], "detail": detail}],
        "causal_unavailable": [], "prerequisites": "unknown",
    }


class Response:
    status = 200
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *unused): return False
    def read(self, limit): return self.body[:limit]


class Opener:
    def __init__(self, body): self.body = body
    def open(self, request, timeout): return Response(self.body)


class CaptureObjectiveOccurrenceTests(unittest.TestCase):
    def checker(self, root: Path) -> Path:
        output = root / "phosphor-objective-occurrence-check"
        source = subprocess.run(["git", "-C", str(AG_ROOT), "show", f"{AG_REVISION}:examples/phosphor-objective-occurrence-check"], check=True, capture_output=True).stdout
        output.write_bytes(source); output.chmod(0o700)
        return output

    def test_captures_nonempty_fixture_and_invokes_exact_public_checker(self):
        expected, document = fixture()
        body = json.dumps(document, separators=(",", ":")).encode("ascii")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output = root / "objective.json"
            arguments = ["--url", "http://127.0.0.1:8417/api/v1/objectives/" + "a" * 64,
                         "--output", str(output), "--checker", str(self.checker(root))]
            for name, value in expected.items(): arguments.extend(("--" + name.replace("_", "-"), value))
            with patch.object(MODULE, "build_opener", return_value=Opener(body)):
                self.assertEqual(MODULE.main(arguments), 0)
            self.assertEqual(output.read_bytes(), body)
            self.assertTrue(output.stat().st_size)

    def test_refuses_non_loopback_and_existing_output(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            MODULE.checked_url("https://example.invalid/api/v1/objectives/" + "a" * 64)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "exists.json"; output.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.write_new_regular(output, b"new")


if __name__ == "__main__":
    unittest.main()
