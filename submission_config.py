#!/usr/bin/env python3
"""Configurable registration fields. CLI reports readiness, never field values."""

import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from env_config import read_values

ROOT = Path(__file__).resolve().parent
REGISTRATION_KEYS = {
    "EASYDATA_WECHAT_NICKNAME", "EASYDATA_TEAM_NAME", "EASYDATA_GROUP_NAME",
    "EASYDATA_CERTIFICATE_NICKNAME", "EASYDATA_FORM_URL", "EASYDATA_SCHEDULE_URL",
}
DEFAULTS = {
    "EASYDATA_COURSE_NAME": "Easy Data × AI",
    "EASYDATA_COURSE_RATING": "5",
    "EASYDATA_NOTES_URL_TEMPLATE": "",
}
REQUIRED = {"EASYDATA_WECHAT_NICKNAME", "EASYDATA_TEAM_NAME", "EASYDATA_GROUP_NAME", "EASYDATA_FORM_URL", "EASYDATA_COURSE_NAME"}


def load_profile(environ=None, project_env=None):
    """Read project-scoped registration fields; never access global private.env."""
    environ = os.environ if environ is None else environ
    project_env = ROOT / ".env" if project_env is None else Path(project_env)
    keys = REGISTRATION_KEYS | set(DEFAULTS)
    values = dict(DEFAULTS)
    values.update(read_values(project_env, keys))
    for key in keys:
        if environ.get(key):
            values[key] = environ[key]
    return values


def validate_profile(profile):
    missing = sorted(key for key in REQUIRED if not profile.get(key, "").strip())
    if missing:
        raise ValueError("缺少报名配置：" + ", ".join(missing))
    if profile.get("EASYDATA_COURSE_RATING") not in {"1", "2", "3", "4", "5"}:
        raise ValueError("EASYDATA_COURSE_RATING 必须为 1～5")
    for key in ("EASYDATA_FORM_URL", "EASYDATA_SCHEDULE_URL", "EASYDATA_NOTES_URL_TEMPLATE"):
        value = profile.get(key, "")
        if value:
            url = urlsplit(value.replace("{task}", "1"))
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError(key + " 必须为不含登录凭据的 HTTPS 地址")
    template = profile.get("EASYDATA_NOTES_URL_TEMPLATE", "").replace("{task}", "1")
    if "{" in template or "}" in template:
        raise ValueError("笔记链接模板只支持 {task} 占位符")


def form_fields(task, profile=None):
    """Build in-memory field values for an authorized form-filling caller."""
    if not isinstance(task, int) or isinstance(task, bool) or task < 1:
        raise ValueError("Task 必须为正整数")
    profile = load_profile() if profile is None else profile
    validate_profile(profile)
    return {
        "微信昵称": profile["EASYDATA_WECHAT_NICKNAME"],
        "队名": profile["EASYDATA_TEAM_NAME"],
        "所学课程": profile["EASYDATA_COURSE_NAME"],
        "群号": profile["EASYDATA_GROUP_NAME"],
        "任务名称": f"task{task}",
        "课程评价": int(profile["EASYDATA_COURSE_RATING"]),
        "笔记链接": profile.get("EASYDATA_NOTES_URL_TEMPLATE", "").replace("{task}", str(task)) or "无",
        "证书昵称": profile.get("EASYDATA_CERTIFICATE_NICKNAME") or "无",
    }


def main():
    if sys.argv[1:] not in ([], ["--check"]):
        print("用法：python3 submission_config.py --check（仅报告是否配置，不显示值）")
        return 2
    try:
        profile = load_profile()
        for key in sorted(REGISTRATION_KEYS | set(DEFAULTS)):
            print(key + "：" + ("已配置" if profile.get(key) else "未配置"))
        validate_profile(profile)
    except (OSError, ValueError):
        # Avoid echoing filesystem paths, raw config, URLs or parser exception payloads.
        print("报名配置未就绪：检查项目 .env 的必填字段、HTTPS 地址、评分和文件格式。", file=sys.stderr)
        return 2
    print("报名配置就绪；尚未填写或提交表单。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
