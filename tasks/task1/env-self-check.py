#!/usr/bin/env python3
"""Shell、Python、Git、模型 API 自检；仅使用 Python 3 标准库。

用法：
  python3 env-self-check.py --apikey=xxx --base-url=https://example.com/v1 --model=模型名
  python3 env-self-check.py --local-only

也可预设 MODEL_API_BASE_URL、MODEL_API_MODEL，此后只传 --apikey=xxx。
Key 可由 MODEL_API_KEY 环境变量提供，避免进入终端历史和进程参数。
支持 OpenAI 兼容 Chat Completions；不自动猜测平台或选择模型。
接口参考：https://platform.openai.com/docs/api-reference/chat/create
退出码：0=已执行项通过（可能有提醒）；1=检查失败；2=缺少 API 配置。
Python 本身无法启动时，需要从终端的报错判断，脚本无法自行报告。
"""

import argparse
import json
import math
import os
import platform
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """不要将携带 Key 的请求自动转发到其他地址。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run(command, cwd=None):
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                          errors="replace", timeout=10, check=False)


def check_shell():
    shell = os.environ.get("COMSPEC" if os.name == "nt" else "SHELL")
    shell = shell or shutil.which("cmd" if os.name == "nt" else "sh")
    if not shell:
        return "FAIL", "未找到 Shell；请检查安装和 PATH"
    command = [shell, "/d", "/c", "echo Shell_OK"] if os.name == "nt" else [
        shell, "-c", "printf 'Shell_OK\\n'"]
    result = run(command)
    if result.returncode != 0 or "Shell_OK" not in result.stdout.splitlines():
        return "FAIL", "Shell 存在，但执行测试命令失败"
    return "PASS", "{}，命令执行正常".format(shell)


def check_python():
    result = run([sys.executable, "-c", "import json, ssl, urllib.request; print('Python_OK')"])
    if result.returncode != 0 or result.stdout.strip() != "Python_OK":
        return "FAIL", "Python 子进程或标准库检查失败"
    return "PASS", "Python {}；{}（未检查项目第三方依赖）".format(
        platform.python_version(), sys.executable)


def check_git(directory):
    git = shutil.which("git")
    if not git:
        return "FAIL", "未安装 Git 或 PATH 中找不到 git"
    version = run([git, "--version"])
    if version.returncode != 0:
        return "FAIL", "Git 版本命令执行失败"
    prefix = version.stdout.strip()
    if not os.path.isdir(directory):
        return "FAIL", prefix + "；--directory 不是有效目录"
    probe = run([git, "-C", directory, "rev-parse", "--is-inside-work-tree"])
    if probe.returncode != 0:
        # 区分普通非仓库目录与权限、所有权检查等实际错误。
        env = dict(os.environ, LC_ALL="C")
        probe = subprocess.run([git, "-C", directory, "rev-parse", "--is-inside-work-tree"],
                               env=env, capture_output=True, text=True, timeout=10)
        if "not a git repository" in probe.stderr:
            return "WARN", prefix + "；当前目录不是 Git 仓库，安装正常"
        return "FAIL", prefix + "；仓库读取失败，请在目标目录手动执行 git status 排查"
    if probe.stdout.strip() != "true":
        return "WARN", prefix + "；当前目录不是工作树，未检查文件状态"
    status = run([git, "--no-optional-locks", "-C", directory, "status", "--porcelain"])
    if status.returncode != 0:
        return "FAIL", prefix + "；无法读取仓库状态"
    state = "有未提交变更" if status.stdout.strip() else "工作区干净"
    return "PASS", prefix + "；仓库可读，" + state + "（未检查远程权限）"


def endpoint_for(base):
    if any(c.isspace() for c in base):
        raise ValueError("接口地址不能包含空白字符")
    parsed = urllib.parse.urlsplit(base)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("接口地址须包含主机，且不能包含账号、密码、查询参数或片段")
    _ = parsed.port  # 校验端口格式。
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise ValueError("接口地址须使用 HTTPS；仅本机接口允许 HTTP")
    path = parsed.path.rstrip("/")
    if not path:
        path = "/v1"
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def check_api(args):
    if args.local_only:
        return "SKIP", "按 --local-only 跳过，没有发送 API 请求"
    missing = [name for name, value in (("--apikey", args.apikey),
               ("--base-url", args.base_url), ("--model", args.model)) if not value]
    if missing:
        return "SKIP", "缺少 {}；Key 无法推导出接口地址，未发送请求".format("、".join(missing))
    if any(c.isspace() for c in args.apikey) or not args.apikey.isascii():
        return "FAIL", "API Key 格式无效（包含空白或非 ASCII 字符）"
    try:
        endpoint = endpoint_for(args.base_url)
    except ValueError:
        return "FAIL", "接口地址无效；须为 HTTPS 地址，无账号密码、空白、查询参数或片段"
    body = {"model": args.model, "messages": [{"role": "user", "content": "Reply only OK."}],
            "stream": False, args.token_limit_param: args.max_tokens}
    request = urllib.request.Request(endpoint, data=json.dumps(body).encode("utf-8"),
                                     headers={"Authorization": "Bearer " + args.apikey,
                                              "Content-Type": "application/json",
                                              "Accept": "application/json"}, method="POST")
    opener = urllib.request.build_opener(NoRedirect())
    start = time.monotonic()
    try:
        with opener.open(request, timeout=args.timeout) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return "FAIL", "响应超过 1 MiB，停止解析"
        data = json.loads(raw)
        choices = data.get("choices") if isinstance(data, dict) else None
        first = choices[0] if isinstance(choices, list) and choices else None
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return "FAIL", "HTTP 成功但没有有效文本回复；检查接口协议、模型或增大 --max-tokens"
        return "PASS", "收到模型文本回复；耗时 {:.2f}s（不输出响应正文或 Key）".format(
            time.monotonic() - start)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        hints = {400: "请求不兼容；核对模型和 token 参数，可尝试 --token-limit-param=max_completion_tokens",
                 401: "鉴权失败，检查 API Key", 403: "无权限或服务访问受限",
                 404: "接口路径或模型不存在", 429: "限流或额度不足"}
        hint = hints.get(code, "服务端异常" if code >= 500 else "接口请求失败")
        if 300 <= code < 400:
            hint = "接口重定向已阻止；请直接提供最终 API 地址"
        return "FAIL", "HTTP {}：{}".format(code, hint)
    except (socket.timeout, TimeoutError):
        return "FAIL", "网络操作超时（{} 秒），没有自动重试".format(args.timeout)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return "FAIL", "网络操作超时，没有自动重试"
        if isinstance(exc.reason, ssl.SSLError):
            return "FAIL", "TLS 证书校验失败；检查证书链和系统时间"
        return "FAIL", "网络连接失败；检查域名、网络、代理和服务状态"
    except (ValueError, UnicodeError):
        return "FAIL", "响应不是有效 JSON；确认地址为 API 接口而非网页"


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("必须为正整数")
    return number


def positive_timeout(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > 120:
        raise argparse.ArgumentTypeError("必须大于 0 且不超过 120 秒")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apikey", default=os.environ.get("MODEL_API_KEY"), help="API Key，也可设置 MODEL_API_KEY")
    parser.add_argument("--base-url", default=os.environ.get("MODEL_API_BASE_URL"), help="API 基址（通常以 /v1 结尾），也接受完整 /chat/completions 地址")
    parser.add_argument("--model", default=os.environ.get("MODEL_API_MODEL"), help="平台提供的准确模型 ID")
    parser.add_argument("--directory", default=os.getcwd(), help="检查此目录的 Git 状态，默认当前目录")
    parser.add_argument("--timeout", type=positive_timeout, default=30, help="API 网络操作超时秒数，默认 30")
    parser.add_argument("--max-tokens", type=positive_int, default=32, help="生成 token 上限，默认 32；推理模型可能需要提高")
    parser.add_argument("--token-limit-param", choices=("max_tokens", "max_completion_tokens"), default="max_tokens", help="平台支持的 token 上限参数，默认 max_tokens")
    parser.add_argument("--local-only", action="store_true", help="只检查本地，不调用 API")
    args = parser.parse_args(argv)
    print("环境自检：Shell / Python / Git / 模型 API", flush=True)
    labels = {"PASS": "通过", "FAIL": "失败", "WARN": "提醒", "SKIP": "跳过"}
    results = []
    for name, check in (("Shell", check_shell), ("Python", check_python),
                        ("Git", lambda: check_git(args.directory)), ("模型 API", lambda: check_api(args))):
        try:
            state, detail = check()
        except subprocess.TimeoutExpired:
            state, detail = "FAIL", "本地命令执行超过 10 秒，已终止"
        except Exception as exc:
            # 不打印异常正文：服务端、代理或进程错误可能夹带凭据。
            state, detail = "FAIL", "检查异常：{}，未输出可能含敏感信息的详情".format(type(exc).__name__)
        if args.apikey:
            detail = detail.replace(args.apikey, "[REDACTED]")
        detail = "".join(c if c.isprintable() else " " for c in detail)
        print("[{}] {}：{}".format(labels[state], name, detail), flush=True)
        results.append(state)
    print("\n汇总：" + "，".join("{} {}".format(labels[s], results.count(s)) for s in labels))
    if "FAIL" in results:
        return 1
    if "SKIP" in results and not args.local_only:
        print("自检未完成：补齐 API 配置后重跑。")
        return 2
    print("本地自检完成。" if args.local_only else "自检完成。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消自检。", file=sys.stderr)
        sys.exit(130)
