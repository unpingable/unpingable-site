#!/usr/bin/env python3
"""Qualify a hypothetical record-only update in a disposable site copy."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="site-content-qualification-") as name:
    copy = Path(name) / "site"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    releases = {str(p.relative_to(copy)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (copy / "constellation/releases").rglob("*") if p.is_file()}
    source = copy / "status.json"
    data = json.loads(source.read_text())
    data["current"]["name"] = "Hypothetical successor <fixture>"
    data["absd"]["name"] = "Hypothetical ABSD preview"
    data["absd"]["intro"] = "Hypothetical QEMU-only fixture description."
    source.write_text(json.dumps(data))
    for script in ("render_status.py", "render_constellation_meta.py", "render_constellation.py"):
        subprocess.run(["python3", "tools/" + script], cwd=copy, check=True)
        subprocess.run(["python3", "tools/" + script, "--check"], cwd=copy, check=True)
    subprocess.run(["python3", "tools/check_constellation.py"], cwd=copy, check=True)
    for relative in ("index.html", "constellation/index.html", "constellation/status.html"):
        assert "Hypothetical successor &lt;fixture&gt;" in (copy / relative).read_text()
    absd = (copy / "constellation/absd.html").read_text()
    assert 'content="Hypothetical QEMU-only fixture description."' in absd
    assert "Hypothetical ABSD preview" in absd
    assert all(hashlib.sha256((copy / path).read_bytes()).hexdigest() == digest
               for path, digest in releases.items())
    data["current"]["links"][0]["url"] = "javascript:negative-fixture"
    source.write_text(json.dumps(data))
    before = (copy / "index.html").read_bytes()
    result = subprocess.run(["python3", "tools/render_status.py"], cwd=copy,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode != 0
    assert (copy / "index.html").read_bytes() == before
print("Hypothetical record update, metadata propagation, escaping, immutable snapshots and link refusal: PASS; disposable copy removed")
