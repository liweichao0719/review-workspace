# Review Workspace

面向多个 AI 项目的通用人工审查工作区。

平台统一审查流程和基础设施，不强行统一各项目的数据结构与判断标准。RAG、SFT 和
RiskPath 等项目通过独立适配器与任务界面接入。

## 技术栈

- 后端：FastAPI、Pydantic、SQLite
- 前端：React、TypeScript、Vite
- 接入：Python 适配器

## 目录

```text
backend/     FastAPI API、适配器协议和持久化
frontend/    React 审查工作区
docs/        讨论总结、架构决策和后续计划
```

## 扩展边界

公共工作区只负责项目与任务切换、列表、筛选、进度、导航和保存。任务描述通过
`renderer_key` 选择前端任务插件；插件负责解释详情数据、维护专属草稿并生成统一的
审核补丁。后端适配器负责按任务读取、校验数据并生成独立的数据版本指纹，公共存储不
解释业务字段。

新增数据类型时，应新增或扩展 Python 适配器，并在 `frontend/src/tasks` 注册专属任务
组件；不应把新业务字段写入公共工作区。

仓库包含一个默认关闭的合成文章筛选任务，用于验证上述边界。启动后端时设置
`REVIEW_ENABLE_DEMOS=1` 即可在项目列表中显示；模拟数据不包含真实文章，也不会与
FIDIC 审核记录混用。

## 本地启动

FIDIC RAG 适配器默认读取同级目录 `/home/simpleai/RAG`。如果项目位于其他位置，
启动后端前设置：

```bash
export REVIEW_FIDIC_RAG_ROOT=/path/to/RAG
```

后端：

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8010
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。前端默认请求
`http://127.0.0.1:8010/api`。

审核记录保存在 `data/reviews.db`，与 RAG 原始数据分离。每条记录绑定输入数据指纹；
来源文件发生变化后会进入新的审核版本，不会覆盖旧结论。

当前 FIDIC 任务直接读取冻结的 `results/human_gold_dev192_v1/dataset.jsonl`，
包含 192 道开发集题目。审查页面只展示题型、问题、标准答案与完整双语上下文；
检索排名、候选召回和模型初审不属于该任务的审查对象。

## 验证

```bash
cd backend && .venv/bin/python -m pytest tests
cd frontend && npm run build
```

## 当前状态

FIDIC RAG 已完成最终开发集审查入口：

- 读取冻结的 192 题开发集与完整双语证据上下文；
- 页面只审查题型、问题、标准答案与上下文，不混入检索排名或历史候选；
- 人工修改以独立、带数据版本的 SQLite 记录保存，不回写冻结 JSONL；
- 保存时校验状态、题型、问题质量、上下文合法性，以及答案条款引用与上下文的精确对应；
- 支持搜索、状态筛选、自动保存、切题前保存、重启恢复和 JSONL 导出。

旧 SFT 与 RiskPath 数据不再是当前的直接迁移目标。平台先通过合成文章和后续节点—关系
任务验证扩展边界，再接入仍在使用的真实数据源；不能为追求“通用”而复用 FIDIC 的
字段或校验。

详细背景见 [讨论与决策总结](docs/discussion-summary.md)，当前执行状态见
[项目任务](docs/project_tasks.json)。
