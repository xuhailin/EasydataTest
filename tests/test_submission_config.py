"""Registration configuration boundaries; all personal values are fixtures."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import submission_config as config


class SubmissionConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / ".env"
        self.private = self.root / "private/private.env"
        self.private.parent.mkdir(mode=0o700)
        self.private.write_text(
            "EASYDATA_WECHAT_NICKNAME='fixture nickname'\n"
            "EASYDATA_TEAM_NAME=fixture-team\nEASYDATA_GROUP_NAME=fixture-group\n"
            "EASYDATA_FORM_URL=https://example.com/form\n"
            "DEEPSEEK_API_KEY=unrelated-fixture-secret\n"
        )
        self.private.chmod(0o600)

    def load(self, env=None):
        return config.load_profile(env or {}, self.project, self.private)

    def test_scoped_read_and_precedence(self):
        self.project.write_text('EASYDATA_COURSE_NAME="Fixture course"\nEASYDATA_COURSE_RATING=3\n')
        values = self.load({"EASYDATA_WECHAT_NICKNAME": "override", "EASYDATA_COURSE_RATING": "4"})
        self.assertEqual(values["EASYDATA_WECHAT_NICKNAME"], "override")
        self.assertEqual(values["EASYDATA_COURSE_RATING"], "4")
        self.assertEqual(values["EASYDATA_COURSE_NAME"], "Fixture course")
        self.assertNotIn("DEEPSEEK_API_KEY", values)
        self.assertNotIn("unrelated-fixture-secret", str(values))

    def test_no_evaluation_and_correct_task_link(self):
        marker = self.root / "must-not-exist"
        self.project.write_text('EASYDATA_NOTES_URL_TEMPLATE=https://example.com/task{task}/\n')
        values = self.load({"EASYDATA_WECHAT_NICKNAME": "$(touch " + str(marker) + ")"})
        fields = config.form_fields(2, values)
        self.assertFalse(marker.exists())
        self.assertEqual(fields["笔记链接"], "https://example.com/task2/")
        self.assertEqual(fields["任务名称"], "task2")
        self.assertEqual(fields["证书昵称"], "无")

    def test_reject_personal_data_in_project_file_and_bad_permissions(self):
        self.project.write_text('EASYDATA_WECHAT_NICKNAME=fixture\n')
        with self.assertRaises(ValueError):
            self.load()
        self.project.unlink()
        self.private.chmod(0o644)
        with self.assertRaises(ValueError):
            self.load()

    def test_validation_rejects_missing_values_and_credentials_in_url(self):
        values = self.load()
        for updates in ({"EASYDATA_TEAM_NAME": ""}, {"EASYDATA_COURSE_RATING": "6"},
                        {"EASYDATA_FORM_URL": "https://user:fixture-password@example.com"},
                        {"EASYDATA_NOTES_URL_TEMPLATE": "https://example.com/{unknown}"}):
            with self.subTest(updates=list(updates)):
                with self.assertRaises(ValueError):
                    config.validate_profile(dict(values, **updates))

    def test_cli_never_echoes_personal_values_on_success_or_failure(self):
        for malformed in (False, True):
            if malformed:
                self.private.write_text('EASYDATA_WECHAT_NICKNAME="fixture-private-unclosed\n')
            output = io.StringIO()
            with patch.object(config, "ROOT", self.root), patch.object(config, "PRIVATE_ENV", self.private), \
                    patch.dict(config.os.environ, {}, clear=True), patch.object(config.sys, "argv", ["check", "--check"]), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                code = config.main()
            self.assertEqual(code, 2 if malformed else 0)
            self.assertNotIn("fixture", output.getvalue())
            self.assertNotIn("example.com", output.getvalue())


if __name__ == "__main__":
    unittest.main()
