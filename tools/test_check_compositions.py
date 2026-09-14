import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from check_compositions import validate, validate_profiles, validate_releases


class Compositions(unittest.TestCase):
    def release_fixture(self, root: Path) -> Path:
        (root / "constellation/examples").mkdir(parents=True)
        (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "maude"}]}))
        files = {
            "constellation/examples/reader.py": b"reader\n",
            "constellation/examples/setup.sh": b"setup\n",
            "constellation/examples/requirements.txt": b"requirements\n",
        }
        for name, content in files.items():
            (root / name).write_bytes(content)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
        subprocess.run(["git", "add", "constellation"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "example kit"], cwd=root, check=True, capture_output=True)
        kit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        release = root / "constellation/releases/0.1.0-alpha.1"; release.mkdir(parents=True)
        manifest = {
            "schema": "constellation.integration-release-manifest/v1", "manifest_schema_version": 1,
            "suite_version": "0.1.0-alpha.1", "profiles": [{"id": "maude-plan-consultation/v1", "required_components": ["maude"]}],
            "components": [{"id": "maude", "source": "https://example.test/maude.git", "commit": kit}],
            "example_source": {"repository": "https://example.test/site.git", "commit": kit, **{key: value for stem, path in (("reader", "constellation/examples/reader.py"), ("setup", "constellation/examples/setup.sh"), ("requirements", "constellation/examples/requirements.txt")) for key, value in ((stem, path), (f"{stem}_sha256", hashlib.sha256(files[path]).hexdigest()))}},
            "documentation": {"guide": "guide.html"}, "qualification": {"record": "qualification.json"},
        }
        manifest_path = release / "manifest.json"; manifest_path.write_text(json.dumps(manifest, sort_keys=True))
        (release / "guide.html").write_text("<h1>guide</h1>")
        qualification = {"schema": "constellation.integration-qualification/v1", "suite_version": "0.1.0-alpha.1", "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
        (release / "qualification.json").write_text(json.dumps(qualification, sort_keys=True))
        subprocess.run(["git", "add", "constellation"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "release"], cwd=root, check=True, capture_output=True)
        return manifest_path

    def composition(self, capability_ids=("a",), *, example_id="a"):
        return {
            "id": "x", "summary": "X", "maturity": "runnable", "recipe": "recipes.html#one",
            "lost_guarantees": ["No authority"], "refusals": ["Invalid input refuses"],
            "capabilities": {"required": [{"capability": "read", "component_ids": list(capability_ids)}], "optional": []},
            "public_examples": [{"implementation_id": example_id, "source": "https://example.test/source", "example": "recipes.html#one", "state": "fixture"}],
        }

    def test_references_inventory_and_recipe_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [self.composition()]}))
            self.assertEqual(validate(root), 1)

    def test_unknown_component_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json",
                "compositions": [self.composition(("missing",), example_id="missing")]}))
            with self.assertRaises(ValueError): validate(root)

    def test_rejects_copied_catalog_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition(); composition["name"] = "copied catalog field"
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            with self.assertRaises(ValueError): validate(root)

    def test_allows_explicit_deployment_capability_without_catalog_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition()
            composition["capabilities"]["required"].append({
                "capability": "deployment executor", "component_ids": [], "provided_by": "deployment"})
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            self.assertEqual(validate(root), 1)

    def test_refuses_deployment_capability_that_claims_catalog_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            composition = self.composition()
            composition["capabilities"]["required"].append({
                "capability": "deployment executor", "component_ids": ["a"], "provided_by": "deployment"})
            (root / "constellation/compositions.json").write_text(json.dumps({
                "schema": "constellation.compositions/v1", "inventory": "components.json", "compositions": [composition]}))
            with self.assertRaises(ValueError): validate(root)

    def test_versioned_profiles_reference_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            (root / "constellation/integration-profiles.json").write_text(json.dumps({
                "schema": "constellation.integration-profiles/v1", "version": "0.1.0-alpha.1",
                "release_status": "candidate", "profiles": [{"id": "a", "component_ids": ["a"],
                "status": "runnable", "guide": "recipes.html#one"}]}))
            self.assertEqual(validate_profiles(root), 1)

    def test_profiles_allow_independent_prerelease_without_reinterpreting_alpha_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "constellation").mkdir()
            (root / "constellation/components.json").write_text(json.dumps({"components": [{"id": "a"}]}))
            (root / "constellation/recipes.html").write_text('<h2 id="one">One</h2>')
            profile = {"schema": "constellation.integration-profiles/v1", "version": "0.1.0-alpha.2",
                       "release_status": "candidate", "profiles": [{"id": "a", "component_ids": ["a"],
                       "status": "runnable", "guide": "recipes.html#one"}]}
            (root / "constellation/integration-profiles.json").write_text(json.dumps(profile))
            self.assertEqual(validate_profiles(root), 1)
            profile["version"] = "latest"
            (root / "constellation/integration-profiles.json").write_text(json.dumps(profile))
            with self.assertRaises(ValueError): validate_profiles(root)

    def test_profiles_allow_mixed_release_versions_bound_to_their_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); constellation = root / "constellation"
            (constellation / "releases/0.1.0-alpha.1").mkdir(parents=True)
            (constellation / "releases/0.1.0-alpha.2").mkdir(parents=True)
            (constellation / "components.json").write_text(json.dumps({"components": [{"id":"a"}]}))
            (constellation / "guide.html").write_text("guide")
            for version, profile_id in (("0.1.0-alpha.1", "old"), ("0.1.0-alpha.2", "new")):
                release = constellation / "releases" / version
                (release / "guide.html").write_text("guide")
                (release / "manifest.json").write_text(json.dumps({
                    "schema":"constellation.integration-release-manifest/v1",
                    "suite_version":version, "profiles":[{"id":profile_id}]}))
            profiles = {"schema":"constellation.integration-profiles/v1", "version":"0.1.0-alpha.2",
                "release_status":"candidate", "profiles":[
                    {"id":"old","component_ids":["a"],"status":"released-alpha","guide":"guide.html",
                     "release":{"suite_version":"0.1.0-alpha.1","guide":"releases/0.1.0-alpha.1/guide.html","manifest":"releases/0.1.0-alpha.1/manifest.json"}},
                    {"id":"new","component_ids":["a"],"status":"qualified-public-reproduction-tag-pending","guide":"guide.html",
                     "release_candidate":{"suite_version":"0.1.0-alpha.2","guide":"releases/0.1.0-alpha.2/guide.html","manifest":"releases/0.1.0-alpha.2/manifest.json"}}]}
            (constellation / "integration-profiles.json").write_text(json.dumps(profiles))
            self.assertEqual(validate_profiles(root), 2)
            manifest_path = constellation / "releases/0.1.0-alpha.2/manifest.json"
            manifest = json.loads(manifest_path.read_text()); manifest["suite_version"] = "0.1.0-alpha.1"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): validate_profiles(root)
            manifest["suite_version"] = "0.1.0-alpha.2"; manifest["profiles"] = [{"id":"other"}]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): validate_profiles(root)

    def test_release_manifest_binds_pinned_source_tree_and_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.release_fixture(root)
            self.assertEqual(validate_releases(root), 1)

    def test_release_refuses_mismatched_manifest_digest_and_unknown_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_path = self.release_fixture(root)
            qualification_path = manifest_path.parent / "qualification.json"
            qualification = json.loads(qualification_path.read_text()); qualification["manifest_sha256"] = "0" * 64
            qualification_path.write_text(json.dumps(qualification))
            with self.assertRaises(ValueError): validate_releases(root)
            qualification["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            qualification_path.write_text(json.dumps(qualification))
            manifest = json.loads(manifest_path.read_text()); manifest["profiles"][0]["required_components"] = ["unknown"]
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): validate_releases(root)

    def test_release_accepts_exact_external_public_component_example_checkout(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory); manifest_path = self.release_fixture(root)
            external = Path(external_directory)
            (external / "runtime/examples").mkdir(parents=True)
            (external / "runtime/docs").mkdir(parents=True)
            example = b"example\n"; guide = b"guide\n"
            (external / "runtime/examples/saved.py").write_bytes(example)
            (external / "runtime/docs/SAVED.md").write_bytes(guide)
            subprocess.run(["git", "init"], cwd=external, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=external, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=external, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://example.test/nightshift.git"], cwd=external, check=True)
            subprocess.run(["git", "add", "."], cwd=external, check=True)
            subprocess.run(["git", "commit", "-m", "external example"], cwd=external, check=True, capture_output=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=external, check=True, capture_output=True, text=True).stdout.strip()
            manifest = json.loads(manifest_path.read_text())
            manifest["components"][0] = {"id": "maude", "source": "https://example.test/nightshift.git", "commit": commit}
            manifest["example_source"] = {"source_kind": "public_component", "component_id": "maude", "commit": commit,
                "example": "runtime/examples/saved.py", "example_sha256": hashlib.sha256(example).hexdigest(),
                "guide": "runtime/docs/SAVED.md", "guide_sha256": hashlib.sha256(guide).hexdigest()}
            manifest_path.write_text(json.dumps(manifest, sort_keys=True))
            qualification_path = manifest_path.parent / "qualification.json"
            qualification = json.loads(qualification_path.read_text())
            qualification["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            qualification_path.write_text(json.dumps(qualification, sort_keys=True))
            self.assertEqual(validate_releases(root, {"maude": external}), 1)
            with self.assertRaises(ValueError): validate_releases(root)
            # Keep the tested runtime at the original commit while pinning a
            # separately published example revision from its exact repository.
            (external / "runtime/docs/NOTE.md").write_text("example-only addition\n")
            subprocess.run(["git", "add", "runtime/docs/NOTE.md"], cwd=external, check=True)
            subprocess.run(["git", "commit", "-m", "example-only successor"], cwd=external, check=True, capture_output=True)
            example_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=external, check=True, capture_output=True, text=True).stdout.strip()
            manifest["example_source"]["commit"] = example_commit
            self.assertNotEqual(manifest["components"][0]["commit"], example_commit)
            manifest_path.write_text(json.dumps(manifest, sort_keys=True))
            qualification["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            qualification_path.write_text(json.dumps(qualification, sort_keys=True))
            self.assertEqual(validate_releases(root, {"maude": external}), 1)
            manifest["example_source"]["example_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, sort_keys=True))
            with self.assertRaises(ValueError): validate_releases(root, {"maude": external})

    def test_external_example_refuses_wrong_source_identity(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory); manifest_path = self.release_fixture(root)
            external = Path(external_directory); (external / "example").write_text("x")
            subprocess.run(["git", "init"], cwd=external, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=external, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=external, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://example.test/wrong.git"], cwd=external, check=True)
            subprocess.run(["git", "add", "."], cwd=external, check=True)
            subprocess.run(["git", "commit", "-m", "wrong source"], cwd=external, check=True, capture_output=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=external, check=True, capture_output=True, text=True).stdout.strip()
            manifest = json.loads(manifest_path.read_text()); digest = hashlib.sha256(b"x").hexdigest()
            manifest["components"][0] = {"id": "maude", "source": "https://example.test/right.git", "commit": commit}
            manifest["example_source"] = {"source_kind":"public_component","component_id":"maude","commit":commit,
                "example":"example","example_sha256":digest,"guide":"example","guide_sha256":digest}
            manifest_path.write_text(json.dumps(manifest, sort_keys=True))
            with self.assertRaises(ValueError): validate_releases(root, {"maude": external})


if __name__ == "__main__": unittest.main()
