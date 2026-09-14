import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).parents[1] / "constellation/examples/connected_cache/make_inputs.py"
SPEC = importlib.util.spec_from_file_location("connected_cache_inputs", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ConnectedCacheInputsTest(unittest.TestCase):
    SOURCE_RESULTS = [MODULE.MAUDE_REVISION, MODULE.SOURCE_REVISIONS["nq_cli"],
                      MODULE.SOURCE_REVISIONS["nq_helpers"],
                      MODULE.SOURCE_REVISIONS["nightshift"], MODULE.SOURCE_REVISIONS["ag"],
                      MODULE.SOURCE_REVISIONS["docket"], MODULE.SOURCE_REVISIONS["pulse_integration"]]

    def fixture(self, root: Path):
        source = root / "maude"
        (source / "qualification/synthetic_cache").mkdir(parents=True)
        (source / "qualification/synthetic_cache/build_plan.py").write_bytes(b"plan")
        (source / "qualification/synthetic_cache/local_compose_executor.py").write_bytes(b"executor")
        programs = root / "programs"
        programs.mkdir()
        for filename in MODULE.PROGRAMS.values():
            path = programs / filename
            path.write_bytes(filename.encode())
            path.chmod(0o755)
        python = root / "python"
        python.write_bytes(b"python")
        python.chmod(0o755)
        sealer = root / "sealer.py"
        sealer.write_bytes(b"sealer")
        return source, programs, python, sealer

    def test_emits_closed_documents_with_fresh_distinct_occurrences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, programs, python, sealer = self.fixture(root)
            args = type("Args", (), {"maude_source": source, "program_dir": programs,
                "nq_source": source, "nightshift_source": source, "ag_source": source,
                "docket_source": source, "pulse_source": source,
                "python": python, "pulse_launcher_sealer": sealer, "label": "public-example",
                "role_digest": "sha256:" + "a" * 64})()
            with patch.object(MODULE, "source_revision", side_effect=self.SOURCE_RESULTS):
                install, profile = MODULE.make(args)
            self.assertEqual(set(install["programs"]), set(MODULE.PROGRAMS))
            self.assertEqual(install["source_revisions"]["nq_cli"],
                             install["source_revisions"]["nq_helpers"])
            identities = profile["identities"]
            self.assertNotEqual(identities["qualification_occurrence_id"],
                                identities["successor_occurrence_id"])
            self.assertEqual(profile["governance"]["profile_label"],
                             "synthetic-standing-cache-example")
            self.assertEqual(profile["runtime"]["project"], "maude-cache-birthday")

    def test_refuses_wrong_source_revision_before_hashing_programs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, programs, python, sealer = self.fixture(root)
            args = type("Args", (), {"maude_source": source, "program_dir": programs,
                "nq_source": source, "nightshift_source": source, "ag_source": source,
                "docket_source": source, "pulse_source": source,
                "python": python, "pulse_launcher_sealer": sealer, "label": "public-example",
                "role_digest": "sha256:" + "a" * 64})()
            with patch.object(MODULE, "source_revision", return_value="0" * 40):
                with self.assertRaisesRegex(ValueError, "tested public revision"):
                    MODULE.make(args)

    def test_refuses_symlinked_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, programs, python, sealer = self.fixture(root)
            (programs / "nq").unlink()
            (programs / "nq").symlink_to(programs / "docker")
            args = type("Args", (), {"maude_source": source, "program_dir": programs,
                "nq_source": source, "nightshift_source": source, "ag_source": source,
                "docket_source": source, "pulse_source": source,
                "python": python, "pulse_launcher_sealer": sealer, "label": "public-example",
                "role_digest": "sha256:" + "a" * 64})()
            with patch.object(MODULE, "source_revision", side_effect=self.SOURCE_RESULTS):
                with self.assertRaisesRegex(ValueError, "non-symlink"):
                    MODULE.make(args)

    def test_refuses_oversize_regular_file_without_reading_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large"
            with path.open("wb") as output:
                output.truncate(MODULE.MAX_FILE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "bounded regular file"):
                MODULE.digest(path)

    def test_recipe_has_no_undefined_runtime_path_placeholders(self):
        readme = PATH.with_name("README.md").read_text(encoding="utf-8")
        self.assertNotIn("$PYTHON", readme)
        self.assertNotIn("/absolute/sealer.py", readme)
        self.assertNotIn("--unit=connected-cache-example", readme)
        self.assertIn('MANAGER="connected-cache-$LABEL-', readme)
        self.assertIn("Rust 1.94.0", readme)


if __name__ == "__main__":
    unittest.main()
