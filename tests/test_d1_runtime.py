"""Exercise unchanged official demos with an offline model and temporary reports."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from course_runtime import DeepSeekConfig
from tasks.task2 import run_d1

COURSE = Path(__file__).resolve().parents[2] / "easy-data-x-ai"
HAS_DEPS = importlib.util.find_spec("langchain") is not None


@unittest.skipUnless(HAS_DEPS and COURSE.is_dir(), "需要 Task 2 虚拟环境和同级官方课程仓库")
class D1IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        parent = Path(self.temp)
        self.root = parent / "project"
        self.root.mkdir()
        (parent / "easy-data-x-ai").symlink_to(COURSE, target_is_directory=True)
        self.config = DeepSeekConfig("fixture-model", "https://api.deepseek.com", "fixture-secret")
        self.stack.enter_context(patch.object(run_d1, "ROOT", self.root))
        self.stack.enter_context(patch.object(DeepSeekConfig, "load", return_value=self.config))
        self.stack.enter_context(patch.object(socket.socket, "connect", side_effect=AssertionError("禁止网络调用")))
        self.previous_path = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self.previous_path))

    def fake_model(self, *, empty=False, tools=True):
        from langchain_core.messages import AIMessage, AIMessageChunk

        class Model:
            bound = False
            rounds = 0

            def invoke(self, messages, **kwargs):
                return AIMessage(content="" if empty else "离线测试回答")

            def bind_tools(self, functions, **kwargs):
                self.bound = True
                return self

            def stream(self, messages, **kwargs):
                if self.bound and tools and not self.rounds:
                    self.rounds += 1
                    yield AIMessageChunk(content="", tool_call_chunks=[{
                        "name": "query_knowledge_base", "args": '{"query": "检索方式"}',
                        "id": "call_test", "index": 0,
                    }])
                else:
                    yield AIMessageChunk(content="离线")
                    yield AIMessageChunk(content="回答")

        return Model()

    def execute(self, *args, **model_options):
        with patch.object(DeepSeekConfig, "create_chat_model", side_effect=lambda: self.fake_model(**model_options)):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = run_d1.main(list(args))
        paths = sorted((self.root / "tasks/task2/results").glob("*.json"))
        report = json.loads(paths[-1].read_text())
        self.assertEqual(paths[-1].read_text(), paths[-1].with_suffix(".txt").read_text())
        return code, report

    def test_all_official_demos_keep_evidence_and_restore_tool_hook(self):
        # Import under the same guard as production before recording the callback.
        from course_runtime import course_environment
        with course_environment():
            sys.path.insert(0, str(COURSE / "code/D1"))
            module = __import__("d1_4_tool_use_mock")
        original = module.print_tool_result
        previous_env = dict(os.environ)
        for _ in range(2):
            code, report = self.execute()
            self.assertEqual(code, 0)
            self.assertEqual([c["name"] for c in report["examples"]], run_d1.NAMES)
            self.assertTrue(all(c["status"] == "PASS" for c in report["examples"]))
            self.assertEqual(report["examples"][2]["events"][0]["content_chunks"], 2)
            self.assertEqual(len(report["examples"][3]["tool_results"]), 1)
            self.assertEqual(len(report["examples"][3]["events"]), 2)
            self.assertIs(module.print_tool_result, original)
            self.assertEqual(dict(os.environ), previous_env)
        self.assertEqual(len(list((self.root / "tasks/task2/results").glob("*.json"))), 2)

    def test_single_example_and_empty_content_failure(self):
        code, report = self.execute("--example", "d1_1_base", empty=True)
        self.assertEqual(code, 1)
        self.assertEqual(len(report["examples"]), 1)
        self.assertEqual(report["examples"][0]["status"], "FAIL")
        self.assertIn("正文为空", report["examples"][0]["error"])

    def test_missing_tool_execution_cannot_pass(self):
        code, report = self.execute("--example", "d1_4_tool_use_mock", tools=False)
        self.assertEqual(code, 1)
        self.assertIn("完整循环", report["examples"][0]["error"])

    def test_missing_course_is_saved_as_failure(self):
        (self.root.parent / "easy-data-x-ai").unlink()
        code, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(report["examples"][0]["name"], "setup")
        self.assertEqual(report["examples"][0]["status"], "FAIL")

    def test_config_failure_is_saved_without_creating_model(self):
        with patch.object(DeepSeekConfig, "load", side_effect=ValueError("缺少模型配置")):
            code, report = self.execute()
        self.assertEqual(code, 2)
        self.assertEqual(report["examples"][0]["name"], "configuration")
        self.assertEqual(report["examples"][0]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
