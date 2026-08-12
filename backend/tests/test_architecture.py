# backend/tests/test_architecture.py
import ast
import io
import pathlib
import tokenize
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"


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
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [name.name for name in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    if any(
                        module.startswith(f"src.{target}")
                        for target in forbidden[layer]
                    ):
                        violations.append(f"{relative}:{node.lineno}:{module}")
        self.assertEqual([], violations)

    def test_core_has_no_framework_imports(self) -> None:
        frameworks = {
            "fastapi",
            "sqlalchemy",
            "pydantic",
            "pydantic_settings",
            "httpx",
            "apscheduler",
            "google",
            "aiosmtplib",
            "jose",
        }
        violations: list[str] = []
        for layer in ("domain", "application"):
            for path in (SOURCE / layer).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    modules: list[str] = []
                    if isinstance(node, ast.Import):
                        modules = [name.name for name in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules = [node.module]
                    for module in modules:
                        if module.split(".")[0] in frameworks:
                            violations.append(
                                f"{path.relative_to(SOURCE)}:{node.lineno}:{module}"
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
