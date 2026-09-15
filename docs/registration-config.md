# 报名资料配置（支持 fork）

项目不内置任何人的报名账号。fork 后填写自己的环境变量即可；`submission_config.py` 使用标准库，只检查和读取配置，不登录、不填写表单、不提交。

这里的“报名账号”指课程表单里的昵称等字段，不是飞书登录密码。浏览器登录仍由用户完成，不保存 Cookie、验证码或登录凭据。

## 1. 配置个人资料

在当前用户的 `~/.codex/env/private.env` 中添加下列变量，保留该文件已有配置。文件权限必须为 `600`，所在 `~/.codex/env` 目录为 `700`。不要覆盖已有文件，也不要把真实值写入仓库。

```dotenv
EASYDATA_WECHAT_NICKNAME="你的微信昵称"
EASYDATA_TEAM_NAME="你的队名"
EASYDATA_GROUP_NAME="你的群号"
EASYDATA_FORM_URL="https://你的实际表单地址"
# 可选：组队任务安排链接、证书昵称
EASYDATA_SCHEDULE_URL=
EASYDATA_CERTIFICATE_NICKNAME=
```

前四项为必填，其余可以留空。证书昵称为空时使用“无”。地址必须为 HTTPS，且不能内嵌账号密码。

也支持由调用进程传入这些同名环境变量，优先于私密文件；不要把真实值直接写进可被记录的命令行。读取器只提取报名变量，不加载同一私密文件中的模型密钥等其他条目，不执行 dotenv 内容。

## 2. 配置课程和自己的网页

新 fork 首次使用时将 `.env.example` 复制为 `.env`；已有 `.env` 时按需补充，不覆盖原配置。

```dotenv
EASYDATA_COURSE_NAME="Easy Data × AI"
EASYDATA_COURSE_RATING=5
EASYDATA_NOTES_URL_TEMPLATE=https://YOUR_NAME.github.io/YOUR_REPO/task{task}/
```

评分允许 1～5。网页链接可以留空，留空时表单笔记链接为“无”；`{task}` 替换为本次 Task 数字。链接必须在站点实际部署成功后再配置。优先级为非空进程环境变量 > 项目 `.env` > 内置非敏感默认值。

个人字段不从项目 `.env` 读取，发现非空个人字段会提示配置错误。项目 `.env`、用户私密文件均不能提交 Git 或加入 Pages 发布清单。

## 3. 检查与使用

```bash
python3 submission_config.py --check
```

命令只显示各变量“已配置 / 未配置”，不会显示值。退出码 0 表示配置就绪，2 表示缺少必填项、格式或权限不正确；配置就绪不等于已经报名或提交。

已获得表单填写授权的程序或 Agent 可调用 `load_profile()` 读取必要配置，再调用 `form_fields(task_number, profile)` 获得字段映射。不要打印、持久化或将整个返回对象发到日志。该映射只包含固定资料，学习心得和课程反馈仍按本次 Task 的用户正文及真实运行结果分别准备。

本机 `easydata-task-submit` skill 已改为读取此接口，不再内置个人字段。其他用户可以使用自己的表单填写工具调用接口，无需安装该个人 skill。

## fork 后发布自己的成果站

- 替换示例心得与成果为自己的实际内容，调整 `site/tasks.json` 的发布清单；不要把原作者的心得当成自己的。
- 按 [成果站说明](showcase-site.md) 启用自己的 Pages，并把 `EASYDATA_NOTES_URL_TEMPLATE` 和 README 入口改为实际部署地址。
- `submission.md` 仅保存可公开的提交结果摘要，报名个人资料继续留在环境配置中。
