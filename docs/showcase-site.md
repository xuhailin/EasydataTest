# 学习成果站

## 范围与状态

- 用户已确认：链接用于查看各 Task 的成果和心得。
- 首页为任务目录，Task 1～10 各有固定页面；Task 10 仍为预留。
- 2026-09-15 用户已将仓库改为 **PUBLIC**，Pages 已启用 GitHub Actions 发布来源，地址为 <https://xuhailin.github.io/EasydataTest/>。部署结果以本文发布记录及实际 Actions 运行为准。
- 2026-09-15 用户授权检查并调整敏感信息后发布 GitHub Pages；仓库可见性由用户自行改为公开。本次发布所需提交、推送与 Pages 配置在此授权范围内。
- 页面中的“已收录”只表示有可展示内容，不代表课程完成或表单已提交。

## 内容如何维护

| 内容 | 维护位置 |
| --- | --- |
| 任务顺序、展示标题、对应章节、公开文件清单 | `site/tasks.json` |
| 对外展示的实践成果摘要 | `tasks/taskN/showcase.md`，引用真实报告中的事实 |
| 学习心得 | 原有 `tasks/taskN/notes.md`，不维护第二份副本 |
| 任务要求与实际完成状态 | 原有 `tasks/taskN/README.md`，仍为权威记录 |
| 构建与样式 | `site/build.py`、`site/style.css` |

补充一个 Task 时：

1. 依据实际产物编写该 Task 的 `showcase.md`。只有心得时，可以暂时不写成果摘要。
2. 将要展示的文件登记到 `site/tasks.json`：`result` 指向成果文件，`notes` 指向心得文件。路径均相对于 `tasks/taskN/`。
3. 报告、截图等逐个加入该 Task 的 `attachments` 列表，再从 Markdown 中使用相对链接引用。
4. 本地构建并检查目标 Task 页面：确认显示“心得已收录”或“成果与心得已收录”，且本次新增正文已出现在 HTML 中；笔记分篇需先合并到清单指定的 `notes.md`，旧文件可保留导航入口，避免维护两份正文。
5. 推送后确认对应提交的部署成功，再访问线上目标页面核对新增正文。Git 推送成功、Actions 成功都不能单独证明内容已收录。

新增笔记不会自动公开，必须先登记到清单。已经登记的心得文件，其后续更新会进入下一次构建；不要在其中加入不打算公开的内容。成果摘要与真实证据不一致时，以实际报告为准并修正摘要。

构建仅导出清单选中的 Markdown 和附件，不复制整个仓库。不导出 `submission.md`、任务 README、配置文件、其他日志、Python 脚本或私密文件。内部相对链接若未对应已选中的发布文件，会使构建失败，避免生成打不开的链接。外部 HTTP(S) 链接保留，构建不检测外部网站可用性。

## 本地预览

站点生成单独使用 Python-Markdown；Task 1 运行入口仍只依赖标准库。需要 Python 3.9+，CI 使用 Python 3.12。

```bash
python3 -m venv .venv-site
.venv-site/bin/python -m pip install -r site/requirements.txt
.venv-site/bin/python site/build.py
.venv-site/bin/python -m http.server 8765 --bind 127.0.0.1 --directory _site
```

访问 <http://127.0.0.1:8765/>。修改 Markdown 后重新执行构建并刷新。生成目录 `_site/` 和站点虚拟环境均被 Git 忽略。

构建时校验所有本地文件链接及页内锚点；失败时不替换已有 `_site/`。页面使用相对链接，可放在 GitHub Pages 项目子路径下，也可在本地根路径预览。

## GitHub Pages 发布配置

工作流在 `.github/workflows/pages.yml`，监听 `main` 分支中的站点及 Task 更新，也支持手动触发。默认只构建；仓库变量 `PUBLISH_PAGES` 为 `true` 时才执行部署。

本仓库已获得发布授权。其他 fork 可按以下步骤完成上线：

1. 核实当前账号能否从私有仓库使用 Pages。GitHub Free 支持公开仓库；私有仓库需要支持相应功能的套餐。不能为此自动公开整个仓库。若现有套餐不支持，可另行选择仅存放生成网页的公开仓库，需单独配置其发布流程。
2. 提交并推送此次站点文件及清单引用的内容，保留和审查原有未提交改动。
3. 在仓库 **Settings → Pages → Build and deployment** 中选择 **GitHub Actions**。
4. 在 **Settings → Secrets and variables → Actions → Variables** 设置 `PUBLISH_PAGES=true`。
5. 手动运行 **Build learning showcase**，或推送新的相关变更。
6. 以部署任务实际返回的 `page_url` 为准，访问首页和每个 Task 页面确认可用，再将文档链接标记为已上线。

按当前仓库名且没有自定义域名时，预计首页为 <https://xuhailin.github.io/EasydataTest/>，Task 链接为 `https://xuhailin.github.io/EasydataTest/taskN/`。实际是否上线以 Actions 部署结果与 HTTP 访问为准。

停止后续自动部署：删除 `PUBLISH_PAGES` 变量或改为 `false`。这不会下线已经发布的网站；下线需在 Pages 设置中另行操作。

参考：[Pages 的能力与套餐](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[自定义发布工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。

## 验收场景

- 首页可进入 10 个 Task，并返回目录或切换相邻任务。
- Task 1 展示实际自检结果与原始报告，保留 API、依赖验证的边界；Task 2 有心得且成果区明确待补充。
- 未收录任务不展示虚构成果，Task 10 保留内容待确认。
- 320、360、390 像素宽度下正文与导航不横向溢出，宽表格可在内部滚动。
- 生成目录只包含清单指定内容及页面资源，无提交资料和配置文件。
- 待发布后验证真实线上地址；本地检查不等同于上线成功或用户验收通过。

## 本次本地验证（2026-09-15）

- Python 3.9.6 构建成功：11 个 HTML 页面、1 份选定报告、CSS、图标和 `.nojekyll`；已校验完整导出文件清单。
- 所有站内链接与锚点通过校验；通过本地 HTTP 服务模拟 `/EasydataTest/` 子路径，11 个页面及资源均返回 200。
- Playwright 检查首页、Task 1、Task 2、Task 10 在 1365、320、360、390 像素宽度下的布局，未发现页面横向溢出；已查看桌面与手机截图，并验证目录进入 Task 1。
- 未登记的内部链接、越出任务目录的文件路径均被构建器拒绝。
- `python3 -m unittest discover -s tests -v`：现有 8 项测试通过。没有修改任务运行入口，也没有调用真实模型 API。
- `git diff --check` 通过。以上为首次本地验证记录，当时尚未提交、推送或部署；后续线上结果见下方发布记录。用户对展示内容的验收仍由实际阅读确认。

## 公开前检查（2026-09-15）

- 已将 Task 1 的详细表单记录保留到仓库外的本机私密目录（目录 700、文件 600），仓库仅保留公开提交摘要。
- 已移除当前文件中的报名昵称等资料、群内表单入口和本机用户名绝对路径。
- 当前文件、现有可达 Git 历史与网页输出经过两轮检查，未发现真实密钥、密码、私钥、手机号、正文邮箱、内网地址或 URL 内嵌凭据；这是本次扫描范围内的结果，不是对未来新增内容的保证。
- 用户已确认将唯一历史提交的作者与提交者邮箱改为 GitHub noreply 邮箱，并授权必要的历史重写与远端更新。重写前已在本机私密目录保存 Git bundle 备份。
- 后续 `submission.md` 只记录公开摘要，完整表单资料留在仓库外。新增待公开材料仍需人工检查。
- 报名字段按用户修正迁移到被 Git 忽略的项目 `.env`（不读取全局 `private.env`），项目提供 [可供 fork 使用的配置说明](registration-config.md) 与只输出状态的检查命令；没有填写或提交表单。

## 报名配置改造验证（2026-09-15）

- 13 项单元测试通过，覆盖固定字段读取优先级、只提取报名变量、不执行配置内容、项目之间配置隔离、不读取全局私密配置、链接模板和检查输出脱敏。
- `./run task1 --local-only`：本地 3 项通过、API 跳过，未调用真实模型。配置解析器抽取为 `env_config.py` 后，原有 Task 1 流程保持可用。
- 实际报名配置检查就绪，真实值没有输出；本次没有填写或提交表单。

## 发布记录（2026-09-15）

- 网站：[学习成果与心得](https://xuhailin.github.io/EasydataTest/)。Task 页面为 `https://xuhailin.github.io/EasydataTest/taskN/`。
- 发布提交：`8f5e330`；[GitHub Actions 部署记录](https://github.com/xuhailin/EasydataTest/actions/runs/34924296870) 的 build、deploy 均成功。
- 线上首页、10 个 Task 页面、CSS、图标与选定报告均返回 HTTP 200，逐文件内容与本地构建一致。
- 仓库 About 首页已设置为成果站；`PUBLISH_PAGES=true` 已配置，后续推送 `main` 中相关内容会触发发布。其他 fork 若修改默认分支，也需要同步调整工作流中的分支名。
- 历史根提交已替换为 `bf50b01`，当前分支所有提交的作者、提交者邮箱使用 GitHub noreply；历史群内任务链接已清理。原始历史仅保留在本机私密备份中，不作为仓库分支或标签推送。该处理不保证 GitHub 的旧提交缓存立即不可访问。
- 本机 `.env` 已配置已验证网站的笔记链接模板，后续按 Task 生成对应网页链接；个人报名字段也从本项目 `.env` 读取。
