#!/usr/bin/env python3
"""Run official D1 demos via shared DeepSeek clients and report storage.

Usage: .venv/bin/python tasks/task2/run_d1.py
Requires tasks/task2/requirements.txt. Makes real model calls.
"""

import argparse
import contextlib
import hashlib
import importlib
import importlib.metadata
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from course_runtime import DeepSeekConfig, ObservedModel, ReportSession, course_environment

NAMES = ["d1_1_base", "d1_2_multi_turn", "d1_3_streaming", "d1_4_tool_use_mock"]


def run_example(name, config, events, tool_results):
    module = importlib.import_module(name)
    with contextlib.ExitStack() as cleanup:
        if name == "d1_4_tool_use_mock":
            original = module.print_tool_result

            def observe_tool(call, result):
                tool_results.append({"name": call["name"], "args": call["args"], "result": result})
                original(call, result)

            module.print_tool_result = observe_tool
            cleanup.callback(setattr, module, "print_tool_result", original)
        llm = ObservedModel(config.create_chat_model(), events)
        return module.run_demo(llm)


def validate_example(name, result, events, tool_results):
    content = "".join(str(c.content) for c in result) if isinstance(result, list) else result.content
    if not content or not str(content).strip():
        raise RuntimeError("模型最终正文为空")
    if name == "d1_3_streaming" and (not events or events[0].get("content_chunks", 0) < 2):
        raise RuntimeError("未观察到多个正文流式分片")
    if name == "d1_4_tool_use_mock" and (not tool_results or len(events) < 2):
        raise RuntimeError("未观察到工具执行和后续模型回答的完整循环")


def main(argv=None):
    parser = argparse.ArgumentParser(description="通过公共 DeepSeek 配置运行官方 D1 示例并保存报告（调用真实 API）")
    parser.add_argument("--example", choices=NAMES, help="仅运行指定示例；默认运行全部四项")
    args = parser.parse_args(argv)
    names = [args.example] if args.example else NAMES
    folder = ROOT / "tasks/task2/results"
    try:
        config = DeepSeekConfig.load(ROOT)
    except (ValueError, OSError) as exc:
        # Configuration errors contain no raw values; filesystem errors may include private paths.
        report = ReportSession(folder, "d1")
        error = exc if isinstance(exc, ValueError) else ValueError("无法读取配置，请检查文件和目录权限。")
        report.add_failure("configuration", error)
        print(f"配置错误：{error}", file=sys.stderr)
        print(f"报告：{report.save()}")
        return 2

    report = ReportSession(folder, "d1", metadata=config.report_metadata(), secrets=(config.api_key,))
    report.data.update(
        adaptation="原样执行官方 run_demo；模型初始化改用项目 DeepSeek 配置。未执行官方 main 的 SiliconFlow 配置入口。",
        tool_protocol="保留官方 d1_4 的 legacy_user_message_fallback=True，工具结果以 user 消息回传，未验证标准 ToolMessage 路径。",
    )
    report.data["limits"].update(tool_rounds=5, max_tokens_per_request=config.max_tokens)
    course = ROOT.parent / "easy-data-x-ai"
    code = course / "code/D1"
    previous_path = sys.path[:]
    try:
        with course_environment():
            report.data["packages"] = {
                name: importlib.metadata.version(name)
                for name in ["langchain", "langchain-openai", "langchain-core", "python-dotenv"]
            }
            report.data["course_commit"] = subprocess.check_output(
                ["git", "-C", str(course), "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE,
            ).strip()
            report.data["source_sha256"] = {
                name: hashlib.sha256((code / name).read_bytes()).hexdigest()
                for name in [*(n + ".py" for n in names), "tool_call_loop.py", "../config.py"]
            }
            sys.path.insert(0, str(code))
            for name in names:
                events = []
                tool_results = []
                report.run_case(
                    name,
                    lambda: run_example(name, config, events, tool_results),
                    validate=lambda result: validate_example(name, result, events, tool_results),
                    details={"events": events, "tool_results": tool_results},
                )
    except Exception as exc:
        report.add_failure("setup", exc)
        print("示例准备失败，详情见报告。", file=sys.stderr)
    finally:
        sys.path[:] = previous_path
    print(f"报告：{report.save()}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
