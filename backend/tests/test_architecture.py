# backend/tests/test_architecture.py
import ast
import io
import pathlib
import sys
import tokenize
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"


def imported_modules(path: pathlib.Path, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [name.name for name in node.names]
    if not isinstance(node, ast.ImportFrom) or not node.module:
        return []
    if node.level == 0:
        return [node.module]
    relative = path.relative_to(SOURCE).with_suffix("")
    package = ("src", *relative.parts[:-1])
    retained = len(package) - node.level + 1
    prefix = package[:max(0, retained)]
    return [".".join((*prefix, *node.module.split(".")))]


class ArchitectureTest(unittest.TestCase):
    def test_dependency_rule(self) -> None:
        forbidden = {
            "domain": ("application", "infrastructure", "presentation", "bootstrap"),
            "application": ("infrastructure", "presentation", "bootstrap"),
            "infrastructure": ("presentation", "bootstrap"),
            "presentation": ("infrastructure", "bootstrap"),
        }
        violations: list[str] = []
        for path in SOURCE.rglob("*.py"):
            relative = path.relative_to(SOURCE)
            layer = relative.parts[0]
            if layer not in forbidden:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                for module in imported_modules(path, node):
                    if any(
                        module.startswith(f"src.{target}")
                        for target in forbidden[layer]
                    ):
                        violations.append(f"{relative}:{node.lineno}:{module}")
        self.assertEqual([], violations)

    def test_core_has_no_external_imports(self) -> None:
        allowed = {"src", *sys.stdlib_module_names}
        violations: list[str] = []
        for layer in ("domain", "application"):
            for path in (SOURCE / layer).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    for module in imported_modules(path, node):
                        if module.split(".")[0] not in allowed:
                            violations.append(
                                f"{path.relative_to(SOURCE)}:{node.lineno}:{module}"
                            )
        self.assertEqual([], violations)

    def test_runtime_settings_are_resolved_only_by_main(self) -> None:
        violations: list[str] = []
        for path in SOURCE.rglob("*.py"):
            if path == SOURCE / "main.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.module != "src.infrastructure.config.settings":
                    continue
                if any(name.name == "get_settings" for name in node.names):
                    violations.append(
                        f"{path.relative_to(SOURCE)}:{node.lineno}:get_settings"
                    )
        self.assertEqual([], violations)

    def test_presentation_does_not_construct_use_cases(self) -> None:
        violations: list[str] = []
        for path in (SOURCE / "presentation").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name.endswith("UseCase"):
                    violations.append(
                        f"{path.relative_to(SOURCE)}:{node.lineno}:{name}"
                    )
        self.assertEqual([], violations)

    def test_source_comments_follow_project_rule(self) -> None:
        violations: list[str] = []
        for path in ROOT.rglob("*.py"):
            if ".test_deps" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            content = path.read_text(encoding="utf-8")
            tokens = tokenize.generate_tokens(io.StringIO(content).readline)
            comments = [token for token in tokens if token.type == tokenize.COMMENT]
            expected = f"# backend/{relative}"
            if not comments or comments[0].start[0] != 1 or comments[0].string != expected:
                violations.append(f"{relative}:missing path header")
            violations.extend(
                f"{relative}:{token.start[0]}:extra comment"
                for token in comments[1:]
            )
        self.assertEqual([], violations)
