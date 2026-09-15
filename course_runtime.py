"""Shared DeepSeek clients and per-task reports; optional SDKs load on demand."""

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import time
from urllib.parse import urlsplit
from uuid import uuid4

from env_config import read_values


@dataclass(frozen=True)
class DeepSeekConfig:
    model: str
    base_url: str
    api_key: str = field(repr=False)
    timeout: float = 90
    max_retries: int = 0
    max_tokens: int = 2048

    @classmethod
    def load(cls, root, private_env=None):
        """Read the same file whitelist as Task 2; never load a whole dotenv file."""
        private = (Path(private_env) if private_env is not None
                   else Path.home() / ".codex/env/private.env")
        config = read_values(Path(root) / ".env", {"MODEL_API_BASE_URL", "MODEL_API_MODEL"})
        if private.exists() and (
            stat.S_IMODE(private.stat().st_mode) != 0o600
            or stat.S_IMODE(private.parent.stat().st_mode) != 0o700
        ):
            raise ValueError("私密配置权限不符：private.env 应为 600，其所在 env 目录应为 700")
        key = read_values(private, {"DEEPSEEK_API_KEY"}).get("DEEPSEEK_API_KEY", "").strip()
        model = config.get("MODEL_API_MODEL", "").strip()
        base = config.get("MODEL_API_BASE_URL", "").strip()
        try:
            parsed = urlsplit(base)
            valid_url = (
                parsed.scheme == "https" and parsed.hostname == "api.deepseek.com"
                and parsed.port in (None, 443) and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment and parsed.path in ("", "/", "/v1", "/v1/")
            )
        except ValueError:
            valid_url = False
        if not key or not model or not valid_url:
            raise ValueError("需要有效的项目 DeepSeek 模型配置和私密文件中的 DEEPSEEK_API_KEY。")
        return cls(model=model, base_url=base, api_key=key)

    def create_chat_model(self):
        """Native LangChain model, suitable for run_demo(llm) or agent builders."""
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=self.model, base_url=self.base_url, api_key=self.api_key,
            timeout=self.timeout, max_retries=self.max_retries, max_tokens=self.max_tokens,
            extra_body={"thinking": {"type": "disabled"}},
        )

    def create_openai_client(self):
        """Native OpenAI client; callers pass config.model in each chat request."""
        from openai import OpenAI

        return OpenAI(base_url=self.base_url, api_key=self.api_key,
                      timeout=self.timeout, max_retries=self.max_retries)

    def report_metadata(self):
        """Connection settings only; adapters record actual request-level limits."""
        return {
            "model": self.model, "base_url": self.base_url,
            "limits": {"timeout_seconds": self.timeout, "max_retries": self.max_retries},
        }


@contextlib.contextmanager
def course_environment():
    """Disable implicit course dotenv loading and tracing during an adapted run."""
    overrides = {"PYTHON_DOTENV_DISABLED": "1", "LANGCHAIN_TRACING_V2": "false",
                 "LANGSMITH_TRACING": "false"}
    previous = {name: os.environ.get(name) for name in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class ObservedModel:
    """D1-style invoke/stream/bind_tools observer; not a full LangChain proxy."""

    def __init__(self, model, events):
        self.model = model
        self.events = events

    def invoke(self, messages, **kwargs):
        started = time.monotonic()
        response = self.model.invoke(messages, **kwargs)
        self.events.append({"method": "invoke", "input_messages": len(messages),
                            "seconds": round(time.monotonic() - started, 3),
                            "usage": response.usage_metadata})
        return response

    def stream(self, messages, **kwargs):
        started = time.monotonic()
        event = {"method": "stream", "input_messages": len(messages), "chunks": 0,
                 "content_chunks": 0, "tool_calls": []}
        self.events.append(event)
        aggregate = None
        try:
            for chunk in self.model.stream(messages, **kwargs):
                event["chunks"] += 1
                if chunk.content:
                    event["content_chunks"] += 1
                    event.setdefault("first_content_seconds", round(time.monotonic() - started, 3))
                aggregate = chunk if aggregate is None else aggregate + chunk
                yield chunk
        finally:
            event["seconds"] = round(time.monotonic() - started, 3)
            if aggregate is not None:
                event["tool_calls"] = aggregate.tool_calls
                event["usage"] = aggregate.usage_metadata

    def bind_tools(self, tools, **kwargs):
        return ObservedModel(self.model.bind_tools(tools, **kwargs), self.events)


class ReportSession:
    """Capture sequential cases; validation belongs to each task's adapter."""

    def __init__(self, folder, label, *, metadata=None, secrets=()):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
            raise ValueError("报告标签只能包含字母、数字、下划线和连字符")
        self.folder = Path(folder)
        self.label = label
        self._secrets = sorted({s for s in secrets if s}, key=len, reverse=True)
        self.data = dict(metadata or {})
        self.data.update(started_at=datetime.now().astimezone().isoformat(),
                         python=platform.python_version(), platform=platform.system(), examples=[])

    def redact(self, value):
        # Redact before JSON escaping so quoted/backslash-containing keys stay hidden.
        if isinstance(value, str):
            for secret in self._secrets:
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {self.redact(k): self.redact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.redact(item) for item in value]
        return value

    def run_case(self, name, callback, *, validate=None, details=None):
        item = dict(details or {})
        item["name"] = name
        output = io.StringIO()
        started = time.monotonic()
        print(self.redact(f"运行 {name}…"), flush=True)
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = callback()
                if validate is not None:
                    validate(result)
            item["status"] = "PASS"
        except Exception as exc:
            item["status"] = "FAIL"
            item["error"] = type(exc).__name__ + ": " + str(exc)
        item["output"] = output.getvalue()
        item["seconds"] = round(time.monotonic() - started, 3)
        item = self.redact(item)
        self.data["examples"].append(item)
        print(self.redact(f"{name}: {item['status']} ({item['seconds']}s)"), flush=True)
        return item

    def add_failure(self, name, exc):
        item = self.redact({"name": name, "status": "FAIL", "output": "",
                            "error": type(exc).__name__ + ": " + str(exc), "seconds": 0})
        self.data["examples"].append(item)
        return item

    @property
    def exit_code(self):
        cases = self.data["examples"]
        return 0 if cases and all(item["status"] == "PASS" for item in cases) else 1

    def save(self):
        self.data["finished_at"] = datetime.now().astimezone().isoformat()
        self.data = self.redact(self.data)
        serialized = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        self.folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = self.folder / f"{stamp}-{uuid4().hex[:8]}-{self.label}.json"
        for target in (path, path.with_suffix(".txt")):
            with target.open("x", encoding="utf-8") as output:
                output.write(serialized)
        return path
