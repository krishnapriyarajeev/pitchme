"""The AI layer must stay usable without the API, so it never imports server."""

import ast
from pathlib import Path

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
