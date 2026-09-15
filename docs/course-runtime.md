# 课程示例共用模型连接与报告

`course_runtime.py` 提供 DeepSeek 模型连接和运行报告保存。Task 2 已接入；后续任务可以调用相同接口，官方示例文件保持原样。

## 已有入口

在本项目根目录执行（会调用真实模型 API）：

```bash
# 四个 D1 示例
.venv/bin/python tasks/task2/run_d1.py

# 只运行基础调用
.venv/bin/python tasks/task2/run_d1.py --example d1_1_base

# 查看选项，不读取密钥、不调用 API
.venv/bin/python tasks/task2/run_d1.py --help
```

请使用本项目 `.venv/bin/python`。其他终端中的 `python` 不一定安装了相同依赖。初次安装见 [Task 2 README](../tasks/task2/README.md)。

## 配置与客户端

`DeepSeekConfig.load(ROOT)` 延续 Task 2 的配置来源：

- 从项目 `.env` 只读 `MODEL_API_BASE_URL`、`MODEL_API_MODEL`。
- 从 `~/.codex/env/private.env` 只读 `DEEPSEEK_API_KEY`，校验文件权限 `600`、目录权限 `700`。
- 当前适配只接受 DeepSeek 官方 HTTPS 地址，基址路径为空或 `/v1`；不把 DeepSeek 密钥发往其他服务。
- 不执行配置文本，也不自动用进程环境覆盖这些文件。Task 1 原有的命令行与环境变量优先级继续由其独立入口负责。

创建客户端不会主动请求模型：

```python
config = DeepSeekConfig.load(ROOT)
llm = config.create_chat_model()       # LangChain ChatOpenAI
client = config.create_openai_client() # 原生 OpenAI 客户端
```

两种客户端默认超时 90 秒、不重试。LangChain 模型还默认最多生成 2048 token，并携带 `thinking: disabled`，与本次 D1 运行设置一致。原生 OpenAI 客户端的模型、生成上限和 thinking 选项需要在每次请求中传入：

```python
with config.create_openai_client() as client:
    response = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": "什么是 RAG？"}],
        max_tokens=config.max_tokens,
        extra_body={"thinking": {"type": "disabled"}},
    )
```

`report_metadata()` 只记录共用的模型、地址、超时和重试设置；任务适配器应按实际请求补充生成上限等记录。Task 2 额外记录了 2048 token 和最多 5 轮工具调用。

公共模块本身只依赖标准库。调用对应工厂才需要 `langchain-openai` 或 `openai`，执行官方 D1 还需要 `langchain` 等课程依赖。当前锁定版本统一见 `tasks/task2/requirements.txt`；后续任务按实际需要声明依赖。

## 后续任务如何保存报告

下面是 `tasks/taskN/` 内脚本的接入结构，示例中的 `demo` 应替换为该任务实际导入的官方模块：

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from course_runtime import DeepSeekConfig, ReportSession, course_environment

config = DeepSeekConfig.load(ROOT)
report = ReportSession(
    Path(__file__).parent / "results", "example",
    metadata=config.report_metadata(), secrets=(config.api_key,),
)

def check_answer(response):
    if not response.content or not str(response.content).strip():
        raise RuntimeError("模型最终正文为空")

with course_environment():
    # 在此导入对应官方模块 demo，避免课程隐式加载其他 .env。
    # from ... import demo
    report.run_case(
        "basic", lambda: demo.run_demo(config.create_chat_model()),
        validate=check_answer,
    )

print(f"报告：{report.save()}")
raise SystemExit(report.exit_code)
```

- `run_case` 捕获标准输出、标准错误和普通异常，失败后可以继续运行后面的用例。
- `validate` 定义该用例的成功条件。未传入时，PASS 仅表示回调没有抛异常；回调返回 `False` 或整数错误码不会自动判失败，任务适配器必须显式检查。
- `details` 可以传入 `events`、`tool_results` 等可 JSON 序列化的数据。用例执行过程中可以往传入的列表追加记录。
- `add_failure(name, exc)` 可记录准备阶段失败。Task 2 已覆盖配置无效、缺依赖和缺课程源码的失败报告；新入口也应处理自己的准备阶段错误。
- `save()` 在任务自己的 `results/` 下生成同内容 JSON 和 TXT，以微秒时间及随机标识避免覆盖旧报告。报告保留 `examples/status/output/error` 等字段。
- 传入 `secrets` 中的密钥在文本输出、错误和嵌套报告数据中脱敏；调用者需传入该次运行实际使用的全部密钥。
- `exit_code`：有用例且全部 PASS 为 0，任何失败或无用例为 1。Task 2 配置错误额外返回 2。
- `course_environment()` 在导入和执行期间禁用隐式 dotenv 加载及 LangChain/LangSmith tracing，退出后恢复原环境；输出捕获和该环境保护适用于顺序执行。

如需 D1 相同的耗时、token 用量、流式分片记录，可使用 `ObservedModel(llm, events)`。它只包装 `invoke`、`stream`、`bind_tools`；需要完整 LangChain 模型接口的 Agent 应直接使用 `create_chat_model()` 返回的原生模型。

## 接入边界

不同官方示例的依赖注入接口不同。D1 接受 `run_demo(llm)`；部分 D4 接受 `run_demo(api_client=...)`，但仍在模块常量中写着供应商模型名，接入时还须显式适配模型名。仅创建共用客户端不会自动改写这些常量。

本次只迁移 Task 2，未批量改写后续章节。数据库、Embedding、RAGAS 和记忆等依赖仍按各任务实际需求配置；聊天模型适配不等于这些能力已经验证。任务编号与 D 章节编号也不能直接对应。

## 本次验收记录

目标：集中复用连接配置及报告保存，保持 Task 2 官方 `run_demo`、默认四项用例、流式和工具调用检查及历史报告格式。

验证方式：标准库离线测试检查配置白名单、权限、SDK 参数、失败及脱敏；Task 2 虚拟环境用模拟模型执行本机官方四个示例，并检查空回答、缺工具调用、准备失败和重复运行的报告。本次验证不读取真实密钥、不调用真实模型 API，不更新任务学习或提交状态。

2026-09-15 验证结果：

- `python3 -m unittest discover -s tests -v`：27 项通过，5 项官方 D1 集成测试因系统 Python 无课程依赖而跳过。
- `.venv/bin/python -m unittest discover -s tests -v`：32 项全部通过，包含上述 5 项官方 D1 离线集成测试。
- `./run task1 --local-only`：本地 3 项通过，API 按要求跳过。
- 使用虚拟密钥和网络阻断检查实际已安装 SDK：两种客户端构造通过；Task 2 `--help` 入口通过。

用户可检查公共模块及本页接入方式；真实 DeepSeek 回归待单独运行，不能由离线测试推断业务验收通过。
