# cuohuatang-mcp

一体化 MCP 服务器：**自动记忆 + 自动总结 + 踩坑本(errlore式) + 纠错台账(AgentRecall式) + Obsidian 嫁接(obsidian-mcp式)**。
免费、免 API key、纯本地，一套工具接入 Claude Code / Cursor / OpenClaw / Hermes / Codex 等所有 MCP 客户端。

> 当前状态：**V0.1 已发布**（GitHub 公开仓库 `cuohuatang/cuohuatang-mcp`，tag v0.1.0）。完整设计见 [DESIGN.md](DESIGN.md)。
> 路线：V0.2（会话交接 + 技能沉淀，18 工具）已实现于 feature 分支，待用户指示后发布。

## 快速开始

```bash
pip install -e ".[dev]"
cuohuatang-mcp --help        # CLI 入口
python -m pytest -q          # 跑测试
```

以 MCP 服务器方式运行：

```bash
# 方式一：源码直接跑
mcp run src/cuohuatang_mcp/server.py

# 方式二（发版后）：从 PyPI 拉取
uvx cuohuatang-mcp
```

## 接入（所有 Agent 同一份 JSON）

```json
{
  "mcpServers": {
    "cuohuatang": {
      "command": "uvx",
      "args": ["cuohuatang-mcp"],
      "env": { "CUOHUATANG_VAULT_PATH": "D:/Obsidian/你的库/vault" }
    }
  }
}
```

Claude Code：`claude mcp add cuohuatang -- uvx cuohuatang-mcp`，或写入 `.mcp.json`。

环境变量均可编辑：`CUOHUATANG_HOME`（默认 `~/.cuohuatang`）、`CUOHUATANG_VAULT_PATH`、`CUOHUATANG_INDEX_PATH`。

## 工具一览（13 个）

| 模块 | 工具 |
|---|---|
| 记忆 | `cm_memory_save` `cm_memory_recall` `cm_memory_search` |
| 总结 | `cm_summarize` `cm_summary_weekly` |
| 踩坑本 | `cm_lesson_add` `cm_lesson_inject` |
| 纠错台账 | `cm_correction_log` `cm_correction_verify` `cm_correction_check` |
| Obsidian | `cm_vault_init` `cm_obsidian_read` `cm_obsidian_write` |

## 检索（V0.1 即混合）

默认 **hybrid = BM25（SQLite FTS5）+ TF-IDF 向量余弦**（纯本地、无外部模型），结果带 `method: bm25/hybrid/vector` 字段可审计；中文经 jieba 分词，`QMT`/`报错`/`QMT 报错`/`行情` 均实测命中。

## 数据（Obsidian 唯一真相源）

```
~/.cuohuatang/vault/           ← markdown 真相源（Obsidian 直接打开）
├── 01-流水账/YYYY-MM-DD.md    ← 记忆
├── 02-踩坑本/<slug>.md        ← 踩坑本（errlore 式，含 [[双链]] 回源）
├── 03-纠错台账/<slug>.md      ← 纠错台账（AgentRecall 式，含 [[双链]] 回源）
└── 04-经验总结/<slug>.md      ← 自动总结
~/.cuohuatang/index.sqlite     ← 检索索引（FTS5 + 向量缓存，可重建）
```

双链约定：`cm_lesson_add(..., links=["01-流水账/2026-10-09"])`、`cm_correction_log(..., links=[...])` → 写入 frontmatter 并在正文渲染 `[[...]]`，Obsidian 图谱互通。

## 许可

MIT © cuohuatang
