import importlib.util
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).parent.parent / "constellation/examples/read_maude_plan.py"
SPEC = importlib.util.spec_from_file_location("read_maude_plan", PATH)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ReaderExample(unittest.TestCase):
    def test_validates_projection_and_current_revision(self):
        revision = {"schema": MODULE.REVISION_SCHEMA, "draft_id": "wanted",
                    "revision_id": "r", "plan_digest": "d"}
        projection = {"schema": MODULE.PROJECTION_SCHEMA, "current_revision": revision,
                      "check_summary": "never_checked", "last_lock_receipt_id": None}
        with patch.object(MODULE, "invoke", return_value=projection) as invoke:
            value = MODULE.inspect("maude-plan", Path("store"), "wanted")
        self.assertEqual(value["availability"], "available")
        self.assertEqual(value["revision_id"], "r")
        invoke.assert_called_once_with("maude-plan", Path("store"), "--read-only", "inspect", "wanted")

    def test_refuses_invalid_projection_summary_and_lock(self):
        revision = {"schema": MODULE.REVISION_SCHEMA, "draft_id": "wanted",
                    "revision_id": "r", "plan_digest": "d"}
        bad_summary = {"schema": MODULE.PROJECTION_SCHEMA, "current_revision": revision,
                       "check_summary": "unknown", "last_lock_receipt_id": None}
        with patch.object(MODULE, "invoke", return_value=bad_summary):
            with self.assertRaises(MODULE.InspectionError):
                MODULE.inspect("maude-plan", Path("store"), "wanted")
        bad_lock = {"schema": MODULE.PROJECTION_SCHEMA, "current_revision": revision,
                    "check_summary": "never_checked", "last_lock_receipt_id": 7}
        with patch.object(MODULE, "invoke", return_value=bad_lock):
            with self.assertRaises(MODULE.InspectionError):
                MODULE.inspect("maude-plan", Path("store"), "wanted")

    def test_enforces_pipe_limit_while_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "emit.py"
            program.write_text(
                "#!/usr/bin/env python3\nimport sys\n"
                f"sys.stdout.buffer.write(b'x' * {MODULE.MAX_OUTPUT + 1})\n",
                encoding="utf-8",
            )
            program.chmod(0o755)
            with self.assertRaisesRegex(MODULE.InspectionError, "output_too_large"):
                MODULE.invoke(str(program), Path(directory) / "store", "inspect", "draft")

    def test_timeout_reaps_program_after_it_closes_both_pipes(self):
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "close-and-wait.py"
            program.write_text(
                "#!/usr/bin/env python3\nimport os, time\n"
                "os.close(1)\nos.close(2)\ntime.sleep(1)\n",
                encoding="utf-8",
            )
            program.chmod(0o755)
            started = time.monotonic()
            with patch.object(MODULE, "TIMEOUT_SECONDS", 0.05):
                with self.assertRaisesRegex(MODULE.InspectionError, "timeout"):
                    MODULE.invoke(str(program), Path(directory) / "store", "inspect", "draft")
            self.assertLess(time.monotonic() - started, 0.5)
