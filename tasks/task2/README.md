# Task 2

- 学习内容：产品篇P1：AI Agent 场景识别 + 开发者篇D1：RAG 产品设计 + 产业应用篇I1：AI 原生数据系统。
- 天数：3 天。
- 截止时间：09月20日 03:00（截图原文，年份和时区未确认）。
- 状态：学习进行中；2026-09-15 已保存用户确认的 [学习心得](notes.md)（D1、I1 相关）。
- 实践与验证：已收录 [实践成果](showcase.md)；P1 完成 4 个问题的阶段性评估，D1 的 d1_1～d1_4 使用真实 DeepSeek 模型运行通过。
- 未完成范围：P1 尚未补足 10 个问题和完整 Checklist；d1_5、d1_6 未运行；I1 数据底座评审按用户选择本次不写，I1 心得保留。
- 提交记录：尚无提交成功记录。

来源见 [课程安排](../../docs/schedule.md)。

## 官方正文对应内容与课后行动

以下按本机官方课程仓库正文核对（2026-09-15）。组队安排中的 D1 标题写作“RAG 产品设计”，但官方 D1 文件为“大模型 API 工程化基础”（正文标题为“大模型 API 基础”）；I1 文件为“AI 原生数据库基础”。章节按 P1、D1、I1 对应，不将 Task 编号等同于章节编号。

| 章节 | 学习重点 | 正文课后行动 |
|---|---|---|
| P1：AI Agent 场景识别 | 判断场景是否适合 Agent，评估数据可得性、任务可定义性及 Agent / Workflow 的选择 | 选一个真实 AI 需求，用 Checklist 评估；列出 10 个典型问题，检查答案数据的位置、存在性、准确性与可访问性，统计立即可用的数量，写出结论并与团队讨论模型层和数据层的投入 |
| D1：大模型 API 工程化基础 | 基础调用、多轮消息、流式输出、Tool Use 与 Agent 循环 | 运行 d1_1～d1_4，再跑通 d1_5 的 seekdb 真实检索工具调用；d1_6 的 create_agent 示例为附加题 |
| I1：AI 原生数据库基础 | 多模数据、LSM-Tree、混合检索、AI Functions、Fork / Diff / Merge | 选一个熟悉的 AI 应用，完成一页“数据底座评审”：列数据类别与检索方式，写明一致性、写后可见性、权限和恢复要求，比较统一数据库与组合架构；如果 Agent 可写数据，补充 Fork → Diff → Merge 审批流程 |

P1 正文另附课后小测，I1 另附 5 道思考题。以上是课程正文的学习与实践内容；组队 Task 2 表单的具体必交项尚未核实，不能直接将所有课后行动标为组队必交作业。

### 本机资料

- [P1 正文](../../../easy-data-x-ai/docs/pm/P1%20课程稿：AI%20Agent%20场景识别.md)
- [D1 正文](../../../easy-data-x-ai/docs/dev/D1%20课程稿：大模型%20API%20工程化基础.md)
- [D1 示例代码](../../../easy-data-x-ai/code/D1)
- [I1 正文](../../../easy-data-x-ai/docs/industry/I1%20课程稿：AI%20原生数据库基础.md)

## 实践记录与复现

- [P1 场景评估](p1-assessment.md)：根据用户真实工作流程整理，事实和助手分析分开标明。
- [D1 成功报告](results/20260915-113114-d1.json)：4 项通过、0 项失败、0 项跳过；5 次真实模型请求。
- [首次失败报告](results/20260915-113034-d1.json)：缺少 SOCKS 代理依赖，模型客户端初始化失败，未发送模型请求；补装 socksio 后重跑通过。
- [任务运行脚本](run_d1.py) 与 [本次依赖版本](requirements.txt)。官方源码保持原样，复用官方 run_demo，模型初始化改用项目 DeepSeek 配置。d1_4 使用模拟知识库及官方 legacy user 消息回传模式。

从项目根目录执行（会调用真实模型 API）：

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r tasks/task2/requirements.txt
.venv/bin/python tasks/task2/run_d1.py
```

需有同级官方课程仓库；本次使用课程提交 `705e32bd071e79a94b805adf71ae6c377da75c98`，报告保留源码哈希。运行脚本只从项目 .env 读取 MODEL_API_BASE_URL、MODEL_API_MODEL，从用户私密配置读取 DEEPSEEK_API_KEY，不回显或保存密钥；不改动根目录 run 或 Task 1 运行入口。

2026-09-15：Python 3.11.15、macOS；LangChain 1.4.0，langchain-openai 1.6.2，依赖一致性检查通过。实际报告中的 PASS 表示上述调用链路检查通过，不代表模型回答已完成全面事实评测或课程整体验收。

## 成果与心得网页

[在线查看 Task 2](https://xuhailin.github.io/EasydataTest/task2/) · [站点维护与本地预览](../../docs/showcase-site.md)
