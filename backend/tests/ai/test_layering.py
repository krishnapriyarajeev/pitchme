"""The AI layer must stay usable without the API, so it never imports server."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import ai

AI_ROOT = Path(ai.__file__).parent


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def test_ai_does_not_import_server():
    offenders = {
        str(path.relative_to(AI_ROOT.parent)): sorted(
            m for m in _imported_modules(path) if m == "server" or m.startswith("server.")
        )
        for path in AI_ROOT.rglob("*.py")
    }
    assert {file: mods for file, mods in offenders.items() if mods} == {}


def test_check_sees_the_whole_package():
    assert len(list(AI_ROOT.rglob("*.py"))) >= 10


# Packages whose imports need only the base install plus the llm extra.
LIGHT_PACKAGES = [
    "ai.analysis",
    "ai.content",
    "ai.core",
    "ai.diarize",
    "ai.rehearsal",
    "ai.providers",
    "ai.speech",
    "ai.transcribe",
    "ai.voice_cloning",
]


@pytest.mark.parametrize("package", LIGHT_PACKAGES)
def test_each_package_imports_on_its_own(package):
    """In a fresh interpreter, so a circular import cannot hide behind the
    order other tests happened to import things in."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {package}"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr.strip().splitlines()[-1]
