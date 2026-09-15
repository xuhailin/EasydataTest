#!/usr/bin/env python3
"""Run official D1 demos with the project's configured model and save evidence.

Usage: .venv/bin/python tasks/task2/run_d1.py
Requires langchain, langchain-openai, python-dotenv (see requirements.txt).
Makes real model calls. Reads only the required configuration keys.
"""

import contextlib
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from env_config import read_values


class ObservedModel:
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
        for chunk in self.model.stream(messages, **kwargs):
            event["chunks"] += 1
            if chunk.content:
                event["content_chunks"] += 1
                event.setdefault("first_content_seconds", round(time.monotonic() - started, 3))
            aggregate = chunk if aggregate is None else aggregate + chunk
            yield chunk
        event["seconds"] = round(time.monotonic() - started, 3)
        if aggregate is not None:
            event["tool_calls"] = aggregate.tool_calls
            event["usage"] = aggregate.usage_metadata

    def bind_tools(self, tools, **kwargs):
        return ObservedModel(self.model.bind_tools(tools, **kwargs), self.events)


def main():
    config = read_values(ROOT / ".env", {"MODEL_API_BASE_URL", "MODEL_API_MODEL"})
    secrets = read_values(Path.home() / ".codex/env/private.env", {"DEEPSEEK_API_KEY"})
    key = secrets.get("DEEPSEEK_API_KEY", "")
    base = config.get("MODEL_API_BASE_URL", "")
    model_name = config.get("MODEL_API_MODEL", "")
    parsed = urlsplit(base)
    if not key or not model_name or parsed.scheme != "https" or parsed.hostname != "api.deepseek.com" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit("需要有效的项目 DeepSeek 模型配置和私密文件中的 DEEPSEEK_API_KEY。")

    # Prevent imported course config from loading unrelated dotenv files or traces.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
    from langchain_openai import ChatOpenAI

    course = ROOT.parent / "easy-data-x-ai"
    code = course / "code/D1"
    sys.path.insert(0, str(code))
    names = ["d1_1_base", "d1_2_multi_turn", "d1_3_streaming", "d1_4_tool_use_mock"]
    commit = subprocess.check_output(["git", "-C", str(course), "rev-parse", "HEAD"], text=True).strip()
    report = {
        "started_at": datetime.now().astimezone().isoformat(),
        "python": platform.python_version(), "platform": platform.system(),
        "packages": {name: importlib.metadata.version(name) for name in ["langchain", "langchain-openai", "langchain-core", "python-dotenv"]},
        "course_commit": commit, "model": model_name, "base_url": base,
        "adaptation": "原样执行官方 run_demo；模型初始化改用项目 DeepSeek 配置。未执行官方 main 的 SiliconFlow 配置入口。",
        "limits": {"timeout_seconds": 90, "max_retries": 0, "max_tokens_per_request": 2048, "tool_rounds": 5},
        "tool_protocol": "保留官方 d1_4 的 legacy_user_message_fallback=True，工具结果以 user 消息回传，未验证标准 ToolMessage 路径。",
        "source_sha256": {name: hashlib.sha256((code / name).read_bytes()).hexdigest() for name in [*(n + ".py" for n in names), "tool_call_loop.py", "../config.py"]},
        "examples": [],
    }
    for name in names:
        print(f"运行 {name}…", flush=True)
        output = io.StringIO()
        events = []
        tool_results = []
        item = {"name": name, "events": events, "tool_results": tool_results}
        started = time.monotonic()
        try:
            module = importlib.import_module(name)
            if name == "d1_4_tool_use_mock":
                original = module.print_tool_result
                def observe_tool(call, result):
                    tool_results.append({"name": call["name"], "args": call["args"], "result": result})
                    original(call, result)
                module.print_tool_result = observe_tool
            llm = ObservedModel(ChatOpenAI(model=model_name, base_url=base, api_key=key,
                                           timeout=90, max_retries=0, max_tokens=2048,
                                           extra_body={"thinking": {"type": "disabled"}}), events)
            with contextlib.redirect_stdout(output):
                result = module.run_demo(llm)
            content = "".join(str(c.content) for c in result) if isinstance(result, list) else result.content
            if not content or not str(content).strip():
                raise RuntimeError("模型最终正文为空")
            if name == "d1_3_streaming" and events[0]["content_chunks"] < 2:
                raise RuntimeError("未观察到多个正文流式分片")
            if name == "d1_4_tool_use_mock" and (not tool_results or len(events) < 2):
                raise RuntimeError("未观察到工具执行和后续模型回答的完整循环")
            item["status"] = "PASS"
        except Exception as exc:
            item["status"] = "FAIL"
            item["error"] = type(exc).__name__ + ": " + str(exc).replace(key, "[REDACTED]")
        item["output"] = output.getvalue().replace(key, "[REDACTED]")
        item["seconds"] = round(time.monotonic() - started, 3)
        report["examples"].append(item)
        print(f"{name}: {item['status']} ({item['seconds']}s)", flush=True)
    report["finished_at"] = datetime.now().astimezone().isoformat()
    folder = Path(__file__).parent / "results"
    folder.mkdir(exist_ok=True)
    path = folder / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-d1.json")
    serialized = json.dumps(report, ensure_ascii=False, indent=2).replace(key, "[REDACTED]") + "\n"
    path.write_text(serialized)
    # The existing showcase accepts TXT attachments; export identical evidence.
    path.with_suffix(".txt").write_text(serialized)
    print(f"报告：{path.relative_to(ROOT)}")
    return 0 if all(x["status"] == "PASS" for x in report["examples"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
