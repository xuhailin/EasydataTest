# EasyData Agent 学习任务成果

按 Task 归档要求、代码、验证证据、笔记与提交记录。当前已配置 Task 1 执行入口，Task 2～9 根据课程截图建立占位，Task 10 内容待确认。

## 学习资料

- 官方课程仓库：[datawhalechina/easy-data-x-ai](https://github.com/datawhalechina/easy-data-x-ai)。
- 本机克隆位置：`../easy-data-x-ai`（与本项目同级，独立 Git 仓库）。
- [本地课程首页](../easy-data-x-ai/README.md)；[在线课程](https://datawhalechina.github.io/easy-data-x-ai/)。
- [资料关联与 Task 1 要求核对](docs/course-materials.md)。

后续学习先对照官方仓库的正文与示例代码，任务产物、运行报告和个人笔记仍归档在本项目。组队学习的 Task 编号与课程章节编号分开记录，映射以任务安排为准。

## 快速开始

需要 Python 3.9+、Shell 和 Git；Task 1 仅使用 Python 标准库，无需安装依赖。

```bash
# 在项目根目录执行；首次初始化已生成 .env，已有文件不要覆盖。
# 新克隆的仓库执行：cp .env.example .env
./run task1 --local-only
```

配置好密钥后运行完整自检：

```bash
./run task1
# 原命令仍可用，同样加载配置、归档报告：
python3 env-self-check.py
```

每次运行保存到 `tasks/task1/results/<时间戳>.txt`，不覆盖之前的结果。退出码：0=已执行项通过，1=检查失败，2=缺少或无效配置/参数，130=取消。`--local-only` 返回 0 只代表本地检查通过。入口固定检查项目根目录的 Git 状态，从其他目录调用也一致。

## 配置一次，以后自动读取

项目 `.env` 保存模型连接配置和本项目报名资料（不提交 Git）：

```dotenv
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_API_MODEL=deepseek-v4-pro
```

密钥保存在用户私密配置文件 `~/.codex/env/private.env`，由你在本地编辑器中添加或更新这一项，保留其他已有内容：

```dotenv
DEEPSEEK_API_KEY=你的真实密钥
```

该文件权限应为 `600`，所在 `~/.codex/env` 目录为 `700`。若文件还不存在，先创建目录和空文件再编辑；不要用覆盖文件的命令破坏已有配置。本次初始化没有创建、修改或读取你的私密配置。

运行入口只提取 `DEEPSEEK_API_KEY` 并传为子进程的 `MODEL_API_KEY`，不加载其他私密变量。`.env` 不接收密钥。没有密钥时报告会标记 API 跳过并返回 2。

配置优先级：

- Base URL / 模型：命令行参数 > 非空进程环境变量 > 项目 `.env`。
- 密钥：`--apikey` > 非空 `MODEL_API_KEY` > 非空 `DEEPSEEK_API_KEY` > 私密文件中的 `DEEPSEEK_API_KEY`。
- 推荐通过环境配置提供密钥，避免把真实密钥放进命令行历史。

配置支持 `NAME=value`、`export NAME=value`、引号和注释；不支持变量展开、命令替换或多行值。加载文件只在当前检查进程中生效，不修改终端启动配置。切换其他服务时同时设置匹配的地址、模型和密钥。

模型名沿用用户提供的 `deepseek-v4-pro`。2026-09-14 10:42 的[完整自检报告](tasks/task1/results/20260914-104218-482332.txt)记录模型 API 已返回文本，4 项通过、0 项跳过；报告未记录实际模型标识，不单独证明模型版本。脚本使用 OpenAI 兼容 Chat Completions；给定无路径基址时请求 `/v1/chat/completions`。推理模型若耗尽默认生成上限，可按平台要求调整 `--max-tokens` 和 `--token-limit-param`，不要把空回复当成通过。

```bash
./run task1 --help
./run task1 --timeout 60 --max-tokens 256
```

直接运行 `python3 tasks/task1/env-self-check.py` 保持产物的独立性：仅读取已经导出的环境变量，不自动加载文件或归档报告。

## 目录和任务

- `run`：配置加载、Task 1 调用、结果归档。
- `tasks/taskN/README.md`：任务要求、产物入口与完成状态。
- `tasks/task1/notes.md`：阅读记录及用户心得。
- `tasks/task1/submission.md`：表单事实材料和提交记录。
- `tasks/task1/results/`：真实自检证据，可随任务成果纳入 Git。
- [课程安排](docs/schedule.md)、[任务流程与设计约定](docs/workflow.md)。

后续任务按需增加自己的脚本、依赖和结果；不是每个学习任务都必须有可执行入口。

## 成果与心得网页

已配置静态成果站：首页列出 Task 1～10，每个 Task 有独立页面。心得复用已有 `notes.md`，成果摘要与附件按发布清单选取。

- [成果站首页](https://xuhailin.github.io/EasydataTest/)
- [内容维护、本地预览与发布说明](docs/showcase-site.md)

仓库已公开，成果站通过 GitHub Actions 发布；部署结果以 Actions 与实际网页为准。具体学习状态仍以各 Task README 与实际证据为准。

## 报名资料配置

fork 后可使用自己的报名资料，无需修改代码。昵称、队名、群号、表单链接、课程和评分统一从本项目 `.env` 读取，不使用全局 `private.env`。模型 API 密钥仍按原规则存放。

- [变量说明与配置步骤](docs/registration-config.md)
- `python3 submission_config.py --check`：仅检查是否配置，不显示真实值，不填写或提交表单。

## 开发验证

```bash
python3 -m unittest discover -s tests -v
./run task1 --local-only
```

自动化验证使用临时配置和本地 HTTP 替身，不读取真实密钥、不调用付费 API。真实 API、导读学习与在线提交分别记录，不能由这些检查推断完成。
