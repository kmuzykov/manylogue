"""Packaging leak tripwire.

uv_build does not consult .gitignore: anything under src/manylogue ships unless
excluded in pyproject. This test builds the real artifacts and fails on any file
outside the allowlist — the class of leak it exists for is a stray .env or chat
.jsonl landing in a published wheel.
"""

import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent

# Everything a wheel may contain. Anything else is a packaging leak.
_ALLOWED_WHEEL = [re.compile(p) for p in (
    r"^manylogue-[^/]+\.dist-info/.+$",
    r"^manylogue/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.py$",
    r"^manylogue/templates/[A-Za-z0-9_-]+\.html$",
    r"^manylogue/static/[A-Za-z0-9_-]+\.css$",
    r"^manylogue/defaults/agents/[A-Za-z0-9_-]+\.toml$",
    r"^manylogue/defaults/roles/[A-Za-z0-9_-]+\.md$",
)]


@pytest.mark.skipif(shutil.which("uv") is None, reason="requires uv on PATH")
def test_built_artifacts_contain_only_allowlisted_files(tmp_path: Path) -> None:
    # Plain `uv build` builds the sdist first and the wheel from it, so this also
    # exercises the sdist file selection end to end.
    subprocess.run(["uv", "build", "--out-dir", str(tmp_path)],
                   cwd=PROJECT_ROOT, check=True, capture_output=True)

    [wheel] = tmp_path.glob("*.whl")
    wheel_files = [n for n in zipfile.ZipFile(wheel).namelist() if not n.endswith("/")]
    offenders = [n for n in wheel_files
                 if not any(p.match(n) for p in _ALLOWED_WHEEL)]
    assert not offenders, f"unexpected files in wheel: {offenders}"

    [sdist] = tmp_path.glob("*.tar.gz")
    with tarfile.open(sdist) as tar:
        sdist_files = tar.getnames()
    leaks = [n for n in sdist_files if ".env" in n or n.endswith(".jsonl")]
    assert not leaks, f"sensitive files in sdist: {leaks}"
