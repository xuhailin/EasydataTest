# 官方学习资料与 Task 1 核对

## 资料关联

- 官方仓库：https://github.com/datawhalechina/easy-data-x-ai
- 本机位置：`../easy-data-x-ai`，与成果项目同级的独立 Git 克隆。
- 核对日期：2026-09-14；分支：`main`；提交：`705e32bd071e79a94b805adf71ae6c377da75c98`。
- 官方正文、代码以该克隆为学习参考；作业、运行证据、笔记保留在本成果项目。没有更换本项目 origin。
- Task 1～Task 9 是组队学习安排的编号；F、P、D、I、X 是教材章节编号，Task 1 不等于 D1。

从成果项目根目录手动更新资料（本地资料无改动时）：

```bash
git -C ../easy-data-x-ai pull --ff-only
```

## Task 1 对应材料

- [F0：课前闲聊 —— OpenClaw 为什么越用越好用？](../../easy-data-x-ai/docs/base_knowledge/F0%20%E8%AF%BE%E7%A8%8B%E7%A8%BF%EF%BC%9A%E8%AF%BE%E5%89%8D%E9%97%B2%E8%81%8A%20%E2%80%94%E2%80%94%20OpenClaw%20%E4%B8%BA%E4%BB%80%E4%B9%88%E8%B6%8A%E7%94%A8%E8%B6%8A%E5%A5%BD%E7%94%A8%EF%BC%9F.md)
- [F1：AI 必知必会（一） —— 大模型的本质与边界](../../easy-data-x-ai/docs/base_knowledge/F1%20%E8%AF%BE%E7%A8%8B%E7%A8%BF%EF%BC%9AAI%20%E5%BF%85%E7%9F%A5%E5%BF%85%E4%BC%9A%EF%BC%88%E4%B8%80%EF%BC%89%20%E2%80%94%E2%80%94%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E7%9A%84%E6%9C%AC%E8%B4%A8%E4%B8%8E%E8%BE%B9%E7%95%8C.md)
- [F2：AI 必知必会（二） —— AI Agent 全景图](../../easy-data-x-ai/docs/base_knowledge/F2%20%E8%AF%BE%E7%A8%8B%E7%A8%BF%EF%BC%9AAI%20%E5%BF%85%E7%9F%A5%E5%BF%85%E4%BC%9A%EF%BC%88%E4%BA%8C%EF%BC%89%20%E2%80%94%E2%80%94%20AI%20Agent%20%E5%85%A8%E6%99%AF%E5%9B%BE.md)

组队要求来源见 [Task 1](../tasks/task1/README.md)。当前官方仓库未发现 `task1` 目录、`env-self-check.py` 或专门的 Shell 环境自检作业。四项自检属于本项目已记录的组队要求，现有自检脚本是本项目产物。

F0～F2 未要求运行独立 Python/Shell 示例；除正文和视频外还有：

- F1 课后行动：选一个 AI 回答不好的问题，分析缺少的数据，再补充数据观察回答变化；正文另附课后小测。
- F2 课后行动：为当前产品或 AI 工具画能力地图，核对 RAG、Memory、Skill、MCP 及缺失数据；正文另附课后小测。
- 这些活动的实际完成情况仍需用户确认，不由自检报告或已提交记录推断。

## 四项自检检查什么

| 项目 | 本项目实际检查 | 检查边界 |
|---|---|---|
| Shell | 找到当前 Shell，启动子进程执行 `printf 'Shell_OK\n'` 并核对输出 | 确认 Shell 能执行命令；不是 Shell 编程作业 |
| Python | 启动当前 Python 子进程，导入 `json`、`ssl`、`urllib.request` | 没有验证官方第三方依赖，也没有要求 Python 3.11 |
| Git | `git --version`、识别项目工作树、读取 `git status --porcelain` | 不检查 push 权限；未提交变更不算失败 |
| 模型 API | 请求兼容 Chat Completions 的接口，确认返回非空文本 | `--local-only` 会明确跳过；不验证 Tool Use、流式输出等 D1 能力 |

从本成果项目根目录执行：

```bash
./run task1 --local-only  # Shell、Python、Git；跳过真实 API
./run task1              # 四项完整检查，会调用已配置的真实模型
```

已有证据：

- [2026-09-14 10:42 完整报告](../tasks/task1/results/20260914-104218-482332.txt)：4 项通过、0 项跳过。
- [本次本地复核](../tasks/task1/results/20260914-162809-369194.txt)：3 项通过、API 跳过，退出码 0；Shell 为 `/bin/zsh`，Python 为 3.9.6，Git 为 2.39.5。
- 本次没有重新调用真实模型 API。

## 后续 D1 才需要运行的代码

参见 [官方代码说明](../../easy-data-x-ai/code/README.md) 与 [D1 示例目录](../../easy-data-x-ai/code/D1)。本项目安排把 D1 放在 Task 2；截图中 D1 的标题与官方正文不一致，后续按官方章节内容核对，不把它补算为 Task 1。

| 示例 | 内容 |
|---|---|
| `d1_1_base.py` | 基础模型调用 |
| `d1_2_multi_turn.py` | 多轮对话 |
| `d1_3_streaming.py` | 流式输出 |
| `d1_4_tool_use_mock.py` | 使用假工具数据演示 Tool Use（仍需真实模型 API） |
| `d1_5_tool_use_seekdb.py` | 接入 seekdb 的 Tool Use |
| `d1_6_agent.py` | Agent 附加体验 |

官方 `code/README.md` 推荐 Python 3.11，当前 pyseekdb/X2 依赖要求 3.11+。当前自检使用的 Python 3.9.6 只证明本项目标准库脚本可运行，不能据此判定后续官方代码环境就绪。后续实践时再准备独立环境与所需依赖。

官方正文部分配置说明与代码 README 存在差异（例如把 Key 写入脚本）；执行时核对实际代码。用户私密资料仍按本项目规则保存在 `~/.codex/env/private.env`，仅提取所需变量传给进程，不复制进课程仓库。
