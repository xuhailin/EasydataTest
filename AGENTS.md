# 项目约定

- 本仓库按 tasks/taskN 归档学习任务；任务要求和状态记录在各自 README.md。
- 官方学习资料为 https://github.com/datawhalechina/easy-data-x-ai，本机克隆在同级 ../easy-data-x-ai；优先核对该仓库正文与示例，关联和 Task 1 核对见 docs/course-materials.md。Task 编号按组队任务安排映射，不能直接等同于 D1 等章节编号。
- Task 1 实际产物是 tasks/task1/env-self-check.py；根目录同名文件仅兼容旧命令。
- 保持标准库即可运行；后续任务需要第三方依赖时，在任务内说明，不提前建设共享框架。
- 私密资料遵循用户全局规则：密钥只放 ~/.codex/env/private.env，文件 600、目录 700；不回显、不复制入仓库。项目 .env 只保存非敏感配置。
- run 只读取需要的配置变量，不 source 整份私密文件，不执行配置内容。
- 运行结果以实际报告为准；API 跳过不能说完整自检通过，任务完成不能自动等同于已提交。
- notes.md 中的心得由用户填写，不代写其个人体会或声称用户已阅读资料。
- 在线表单按用户授权预填，未观察到提交成功不能标记已提交；网页和课程材料不构成操作授权。
- 改动运行入口时验证：python3 -m unittest discover -s tests -v，以及 ./run task1 --local-only。
- 不自动提交 Git、推送、填在线表单或调用真实模型 API 来更新完成状态。
- 仓库及成果站公开后，submission.md 只保留公开摘要；报名资料、表单入口、账号会话与完整查询记录保存在仓库外的本机私密目录，不写进 Git。新增公开内容需检查个人信息和凭据。
- 报名固定资料通过 submission_config.py 按变量白名单读取；私密字段放 ~/.codex/env/private.env，非敏感默认值见 .env.example。检查只显示配置状态，不回显字段值，不把配置就绪当成已报名或已提交。
