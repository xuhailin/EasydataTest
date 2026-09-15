"""Offline checks for shared model configuration and durable run evidence."""

import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from course_runtime import DeepSeekConfig, ReportSession


class DeepSeekConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.project_env = self.project / ".env"
        self.project_env.write_text(
            "MODEL_API_BASE_URL=https://api.deepseek.com/v1\n"
            "MODEL_API_MODEL=deepseek-chat\n"
            "DEEPSEEK_API_KEY=wrong-project-fixture-key\n"
        )
        self.private_dir = self.root / "private"
        self.private_dir.mkdir(mode=0o700)
        self.private_env = self.private_dir / "private.env"
        self.private_env.write_text("DEEPSEEK_API_KEY=private-fixture-key\n")
        self.private_env.chmod(0o600)

    def load(self):
        return DeepSeekConfig.load(self.project, private_env=self.private_env)

    def test_load_keeps_configuration_sources_separate_and_hides_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "wrong-process-fixture-key"}):
            config = self.load()
        self.assertEqual(config.model, "deepseek-chat")
        self.assertEqual(config.base_url, "https://api.deepseek.com/v1")
        self.assertEqual(config.api_key, "private-fixture-key")
        self.assertNotIn("private-fixture-key", repr(config))

    def test_default_private_file_uses_codex_home_directory(self):
        home = self.root / "home"
        private_dir = home / ".codex" / "env"
        private_dir.mkdir(parents=True, mode=0o700)
        secret_file = private_dir / "private.env"
        secret_file.write_text("DEEPSEEK_API_KEY=default-fixture-key\n")
        secret_file.chmod(0o600)
        with patch.object(Path, "home", return_value=home):
            config = DeepSeekConfig.load(self.project)
        self.assertEqual(config.api_key, "default-fixture-key")

    def test_missing_project_values_fail(self):
        for content in ("", "MODEL_API_MODEL=deepseek-chat\n",
                        "MODEL_API_BASE_URL=https://api.deepseek.com/v1\n"):
            with self.subTest(content=content):
                self.project_env.write_text(content)
                with self.assertRaises(ValueError):
                    self.load()

    def test_missing_private_key_does_not_fall_back_to_project_or_process(self):
        self.private_env.write_text("UNRELATED_KEY=unused-fixture-key\n")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "wrong-process-fixture-key"}):
            with self.assertRaises(ValueError):
                self.load()

    def test_unsafe_urls_are_rejected(self):
        for url in ("http://api.deepseek.com/v1", "https://example.com/v1",
                    "https://api.deepseek.com.example.com/v1",
                    "https://user:fixture-password@api.deepseek.com/v1",
                    "https://api.deepseek.com/v1?token=fixture",
                    "https://api.deepseek.com/v1#fragment"):
            with self.subTest(url=url):
                self.project_env.write_text(
                    f"MODEL_API_BASE_URL='{url}'\nMODEL_API_MODEL=deepseek-chat\n"
                )
                with self.assertRaises(ValueError):
                    self.load()

    def test_private_file_and_directory_permissions_are_required(self):
        for file_mode, directory_mode in ((0o644, 0o700), (0o600, 0o755)):
            with self.subTest(file_mode=file_mode, directory_mode=directory_mode):
                self.private_env.chmod(file_mode)
                self.private_dir.chmod(directory_mode)
                with self.assertRaises(ValueError):
                    self.load()

    def test_sdk_factories_receive_explicit_bounded_parameters(self):
        chat_factory = Mock(return_value=object())
        openai_factory = Mock(return_value=object())
        modules = {
            "langchain_openai": types.SimpleNamespace(ChatOpenAI=chat_factory),
            "openai": types.SimpleNamespace(OpenAI=openai_factory),
        }
        config = self.load()
        with patch.dict(sys.modules, modules):
            self.assertIs(config.create_chat_model(), chat_factory.return_value)
            self.assertIs(config.create_openai_client(), openai_factory.return_value)
        chat_factory.assert_called_once_with(
            model="deepseek-chat", base_url="https://api.deepseek.com/v1",
            api_key="private-fixture-key", timeout=90, max_retries=0,
            max_tokens=2048, extra_body={"thinking": {"type": "disabled"}},
        )
        openai_factory.assert_called_once_with(
            base_url="https://api.deepseek.com/v1", api_key="private-fixture-key",
            timeout=90, max_retries=0,
        )


class ReportSessionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / "results"

    def session(self, **kwargs):
        return ReportSession(self.folder, "fixture", **kwargs)

    def test_empty_session_is_not_a_successful_run(self):
        report = self.session()
        self.assertEqual(report.data["examples"], [])
        self.assertEqual(report.exit_code, 1)

    def test_success_with_none_return_and_validation(self):
        report = self.session()
        first = report.run_case("prints-only", lambda: print("first output"))
        validate = Mock()
        second = report.run_case("value", lambda: "answer", validate=validate)
        validate.assert_called_once_with("answer")
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        self.assertIn("first output", first["output"])
        self.assertEqual(report.exit_code, 0)

    def test_exception_preserves_both_outputs_and_following_cases_still_run(self):
        report = self.session()

        def fail_after_output():
            print("partial standard output")
            print("partial diagnostic output", file=sys.stderr)
            raise RuntimeError("fixture failure")

        item = report.run_case("broken", fail_after_output)
        following = report.run_case("following", lambda: None)
        self.assertEqual(item["status"], "FAIL")
        self.assertIn("partial standard output", item["output"])
        self.assertIn("partial diagnostic output", item["output"])
        self.assertIn("RuntimeError", item["error"])
        self.assertIn("fixture failure", item["error"])
        self.assertEqual(following["status"], "PASS")
        self.assertEqual(report.exit_code, 1)

    def test_validation_failure_keeps_callback_evidence(self):
        report = self.session()

        def validate(result):
            self.assertEqual(result, "empty answer")
            raise ValueError("required content absent")

        def callback():
            print("received empty answer")
            return "empty answer"

        item = report.run_case("invalid", callback, validate=validate)
        self.assertEqual(item["status"], "FAIL")
        self.assertIn("received empty answer", item["output"])
        self.assertIn("required content absent", item["error"])
        self.assertEqual(report.exit_code, 1)

    def test_setup_failure_can_be_saved_without_running_a_callback(self):
        report = self.session()
        report.add_failure("configuration", ValueError("fixture missing config"))
        path = report.save()
        data = json.loads(path.read_text())
        self.assertEqual(data["examples"][0]["status"], "FAIL")
        self.assertIn("fixture missing config", data["examples"][0]["error"])
        self.assertEqual(report.exit_code, 1)

    def test_nested_and_escaped_secrets_are_redacted_before_serialization(self):
        secret = 'fixture-"quoted"\\path\nkey'
        report = self.session(
            metadata={"nested": [{"secret": secret, "message": "prefix " + secret}]},
            secrets=(secret,),
        )

        def callback():
            print(secret)
            print("diagnostic " + secret, file=sys.stderr)
            raise RuntimeError("failed with " + secret)

        report.run_case("redact", callback, details={"nested": [secret, {"key": secret}]})
        path = report.save()
        raw = path.read_text()
        self.assertEqual(raw, path.with_suffix(".txt").read_text())
        data = json.loads(raw)
        self.assertNotIn(secret, str(data))
        self.assertNotIn(json.dumps(secret)[1:-1], raw)
        self.assertNotIn('fixture-', raw)
        self.assertIn("[REDACTED]", raw)
        self.assertEqual(data["examples"][0]["status"], "FAIL")

    def test_each_save_produces_new_matching_json_and_text_files(self):
        report = self.session()
        report.run_case("first", lambda: None)
        first = report.save()
        first_content = first.read_text()
        report.run_case("second", lambda: None)
        second = report.save()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_text(), first_content)
        for path in (first, second):
            self.assertEqual(path.suffix, ".json")
            self.assertEqual(path.read_text(), path.with_suffix(".txt").read_text())
        self.assertEqual(len(json.loads(first_content)["examples"]), 1)
        self.assertEqual(len(json.loads(second.read_text())["examples"]), 2)


if __name__ == "__main__":
    unittest.main()
