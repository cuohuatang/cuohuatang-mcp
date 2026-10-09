# cuohuatang-mcp

一体化 MCP 服务器：**自动记忆 + 自动总结 + 踩坑本(errlore式) + 纠错台账(AgentRecall式) + Obsidian 嫁接(obsidian-mcp式) + 会话交接(session-handoff式) + 技能沉淀(session-to-skill式)**。
免费、免 API key、纯本地，一套工具接入 Claude Code / Cursor / OpenClaw / Hermes / Codex 等所有 MCP 客户端。

> 当前状态：**v0.1+v0.2 设计与骨架**（评审阶段，11 项测试全过）。完整设计见 [DESIGN.md](DESIGN.md)。

## 快速开始（骨架）

```bash
pip install -e ".[dev]"
cuohuatang-mcp --help        # CLI 入口
python -m pytest -q          # 跑骨架测试
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

## 工具一览（18 个）

| 模块 | 工具 |
|---|---|
| 记忆 | `cm_memory_save` `cm_memory_recall` `cm_memory_search` |
| 总结 | `cm_summarize` `cm_summary_weekly` |
| 踩坑本 | `cm_lesson_add` `cm_lesson_inject` |
| 纠错台账 | `cm_correction_log` `cm_correction_verify` `cm_correction_check` |
| Obsidian | `cm_vault_init` `cm_obsidian_read` `cm_obsidian_write` |
| 会话交接 | `cm_handoff_create` `cm_handoff_list` `cm_handoff_resume` |
| 技能沉淀 | `cm_skill_suggest` `cm_skill_propose` |

## 数据位置

- vault（markdown，Obsidian 可直接打开）：`CUOHUATANG_VAULT_PATH`，默认 `~/.cuohuatang/vault`
- 检索索引（可重建）：`~/.cuohuatang/index.sqlite`

## 许可

MIT © cuohuatang
