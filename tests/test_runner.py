"""验证配置与报告链路；真实任务脚本配合本地 HTTP 替身。"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("task_runner", str(PROJECT / "run"))
spec = importlib.util.spec_from_loader(loader.name, loader)
runner = importlib.util.module_from_spec(spec)
loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.contexts = contextlib.ExitStack()
        self.addCleanup(self.contexts.close)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        task = self.root / "tasks/task1"
        task.mkdir(parents=True)
        shutil.copyfile(PROJECT / "tasks/task1/env-self-check.py", task / "env-self-check.py")
        self.private = self.root / "private/private.env"
        self.private.parent.mkdir(mode=0o700)
        self.contexts.enter_context(patch.object(runner, "ROOT", self.root))
        self.contexts.enter_context(patch.object(runner, "PRIVATE_ENV", self.private))
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in runner.PUBLIC_KEYS | {"MODEL_API_KEY", "DEEPSEEK_API_KEY"}}
        self.contexts.enter_context(patch.dict(os.environ, clean_env, clear=True))

    def write_key(self, text="DEEPSEEK_API_KEY=fixture-secret\n"):
        self.private.write_text(text, encoding="utf-8")
        self.private.chmod(0o600)

    def execute(self, *arguments):
        before = set(self.root.glob("tasks/task1/results/*.txt"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = runner.main(["task1", *arguments])
        created = set(self.root.glob("tasks/task1/results/*.txt")) - before
        self.assertEqual(len(created), 1)
        return code, output.getvalue(), created.pop().read_text(encoding="utf-8")

    def server(self, status=200):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, self.headers.get("Authorization"), body))
                response = {"choices": [{"message": {"content": "OK"}}]}
                data = json.dumps(response).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()

        def stop():
            server.shutdown()
            server.server_close()
            worker.join()

        self.addCleanup(stop)
        (self.root / ".env").write_text(
            "MODEL_API_BASE_URL=http://127.0.0.1:{}\nMODEL_API_MODEL=fixture-model\n".format(
                server.server_address[1]), encoding="utf-8")
        # 确保测试只访问本地替身，不受本机代理设置影响。
        self.contexts.enter_context(patch.dict(os.environ, {"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"}))
        return requests

    def test_missing_key_is_incomplete_and_reported(self):
        code, output, report = self.execute()
        self.assertEqual(code, 2)
        self.assertIn("[跳过] 模型 API", report)
        self.assertIn("自检未完成", output)
        self.assertIn("退出码：2", report)

    def test_local_only_ignores_private_file_and_keeps_each_run(self):
        self.private.write_bytes(b"\xff invalid private config")
        self.private.chmod(0o644)
        for _ in range(2):
            code, _, report = self.execute("--local-only")
            self.assertEqual(code, 0)
            self.assertIn("不代表模型 API 已通过", report)
            self.assertIn("[跳过] 模型 API", report)
        self.assertEqual(len(list(self.root.glob("tasks/task1/results/*.txt"))), 2)

    def test_private_key_reaches_api_without_leaking(self):
        requests = self.server()
        self.write_key("UNRELATED='malformed\nDEEPSEEK_API_KEY='fixture-secret' # comment\n")
        code, output, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(requests[0][0], "/v1/chat/completions")
        self.assertEqual(requests[0][1], "Bearer fixture-secret")
        self.assertEqual(requests[0][2]["model"], "fixture-model")
        self.assertIn("[通过] 模型 API", report)
        self.assertNotIn("fixture-secret", output + report)

    def test_cli_overrides_environment_and_dotenv(self):
        requests = self.server()
        self.write_key()
        with patch.dict(os.environ, {"MODEL_API_KEY": "environment-secret", "MODEL_API_MODEL": "env-model"}):
            code, output, report = self.execute("--apikey=cli-secret", "--model=cli-model")
        self.assertEqual(code, 0)
        self.assertEqual(requests[0][1], "Bearer cli-secret")
        self.assertEqual(requests[0][2]["model"], "cli-model")
        self.assertNotIn("cli-secret", output + report)

    def test_environment_overrides_files_and_skips_private_read(self):
        self.write_key()
        self.private.chmod(0o644)
        (self.root / ".env").write_text("MODEL_API_MODEL=file-model\n", encoding="utf-8")
        with patch.dict(os.environ, {"MODEL_API_KEY": "env-secret", "MODEL_API_MODEL": "env-model"}):
            env = runner.task_environment([])
        self.assertEqual(env["MODEL_API_KEY"], "env-secret")
        self.assertEqual(env["MODEL_API_MODEL"], "env-model")

    def test_http_failure_propagates_to_report_and_exit(self):
        requests = self.server(status=401)
        self.write_key()
        code, output, report = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(len(requests), 1)
        self.assertIn("HTTP 401", report)
        self.assertIn("退出码：1", report)
        self.assertNotIn("fixture-secret", output + report)

    def test_config_error_is_redacted(self):
        self.write_key("DEEPSEEK_API_KEY='fixture-secret\n")
        code, output, report = self.execute()
        self.assertEqual(code, 2)
        self.assertIn("配置错误", report)
        self.assertNotIn("fixture-secret", output + report)

    def test_config_is_data_and_unrelated_secrets_are_not_loaded(self):
        self.write_key("DEEPSEEK_API_KEY='$(touch should-not-exist)'\nOTHER_SECRET=unrelated\n")
        env = runner.task_environment([])
        self.assertEqual(env["MODEL_API_KEY"], "$(touch should-not-exist)")
        self.assertNotIn("OTHER_SECRET", env)
        self.assertFalse((self.root / "should-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
