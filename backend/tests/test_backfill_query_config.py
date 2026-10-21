# backend/tests/test_backfill_query_config.py
import ast
import importlib
import inspect
import unittest
from pathlib import Path

from src.application.services.query_config import QueryConfig


class BackfillQueryConfigurationTest(unittest.TestCase):
    def test_report_backfills_supply_the_current_query_configuration_without_execution(self):
        for name in ("backfill_annual_redeployment", "backfill_unlimited_dashboard_widgets"):
            with self.subTest(script=name):
                module = importlib.import_module(f"scripts.{name}")
                tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
                calls = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "QueryConfig"
                ]
                self.assertEqual(1, len(calls))
                call = calls[0]
                keywords = {value.arg: value.value for value in call.keywords}
                inspect.signature(QueryConfig).bind(*[None for value in call.args], **dict.fromkeys(keywords))
                for field, symbol, expected in (
                    ("redeployment_flag_field", "REDEPLOYMENT_FLAG_FIELD", "cf[11819]"),
                    ("redeployment_month_field", "REDEPLOYMENT_MONTH_FIELD", "cf[12421]"),
                ):
                    value = keywords[field]
                    self.assertIsInstance(value, ast.Call)
                    self.assertEqual("jql_field", value.func.id)
                    self.assertEqual(1, len(value.args))
                    self.assertEqual(symbol, value.args[0].id)
                    self.assertEqual(expected, module.jql_field(getattr(module, symbol)))
