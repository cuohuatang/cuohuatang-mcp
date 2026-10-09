# cuohuatang-mcp 设计文档（V0.1 发布版）

> 状态：**V0.1 已发布**（GitHub 公开仓库 `cuohuatang/cuohuatang-mcp`，tag v0.1.0）
> 技术栈：Python 3.10+（`mcp>=2.0`，MCPServer API）
> 目标仓库：`cuohuatang/cuohuatang-mcp`（GitHub 公开）
> 许可：MIT
> 版本节奏：V0.2（会话交接 + 技能沉淀）已在 feature 分支 `feature/v0.2-handoff-skillcraft` 实现并验证，**待用户指示后发布**（见附录 A）

---

## 1. 定位

一个**免费、免 API key、纯本地**的一体化 MCP 服务器：把 Agent 的「自动记忆 + 自动总结 + 自动纠错（踩坑本/纠错台账）+ Obsidian 嫁接」合并为**一套代码、一组 `cm_` 工具**，装一次即可接入 Claude Code / Cursor / OpenClaw / Hermes / Codex 等所有 MCP 客户端。

核心思想：**不要让每个工具各存各的**。所有记忆、教训、纠正最终都写入 Obsidian 兼容的 markdown 文件，Obsidian 作为唯一真相源（Single Source of Truth）；任何 Agent 通过本服务器读写同一个 vault，等于共用一个大脑。

## 2. 设计原则

| # | 原则 | 说明 |
|---|---|---|
| P1 | 合并不包装 | 不嵌套启动 agentmemory / AgentRecall / obsidian-mcp 进程（stdio 嵌套是坑），而是**取各家功能设计，一套代码重写合并** |
| P2 | 免 key 优先 | 默认零 API key：**混合检索 = BM25（SQLite FTS5）+ TF-IDF 向量余弦（纯本地）**；启发式压缩 |
| P3 | Obsidian 唯一真相源 | 全部数据为 markdown（带 frontmatter + 双链），可直接用 Obsidian 打开；SQLite 仅作检索索引，可随时重建 |
| P4 | 文件式优先 | 参考 errlore「文件式、无服务器」：数据即文件，用户看得见、改得动、搜得到 |
| P5 | 跨 Agent 通用 | 同一份 `mcpServers` JSON 粘贴到每个 Agent 即可，不做任何单工具绑定 |

## 3. 总体架构

```
      Claude Code / Cursor / OpenClaw / Hermes / Codex / ...
                     │  （全部走 MCP stdio）
                     ▼
          ┌────────────────────────────┐
          │      cuohuatang-mcp        │  ← 本服务器（MCPServer, mcp>=2.0）
          │  ┌────────┬───────┬──────┐ │
          │  │ memory │ lessons│corr  │ │  ① 自动记忆  ② 踩坑本(errlore式)
          │  │ (agent │ (errlore│ect  │ │  ③ 纠错台账  ④ 自动总结
          │  │memory式)│  式)  │(Recall│ ⑤ Obsidian 桥梁
          │  │  └──┬──┴──┬───┴─┬─┘  │
          │  └─────┼─────┼─────┼────┘
          │   summarize ┘     │
          └────────┼──────────┼────────┘
                   ▼          ▼
        ┌────────────────┐   ┌──────────────────┐
        │ ~/.cuohuatang/ │   │ index.sqlite     │
        │   vault/       │   │ FTS5(BM25) 索引  │
        │  (markdown)    │   │ + TF-IDF 向量    │
        └────────────────┘   └──────────────────┘
                   │
                   ▼
        Obsidian 打开 vault 即见即改（双链/搜索/标签）
```

## 4. 模块来源对照（去重合并结果）

| cuohuatang-mcp 模块 | 功能来源 | 合并方式 |
|---|---|---|
| memory 自动记忆 | agentmemory | 会话记录 + 上下文召回（**BM25 + TF-IDF 向量混合**） |
| summarize 自动总结 | agentmemory `mem::compress` | 会话压缩 + 每周定期整理（**纯规则聚合**，不接外部 LLM） |
| lessons 踩坑本 | **errlore** | 文件式教训 + 标签 + **按模型信任度** + **Obsidian 双链回源**，开工前自动注入已知错误 |
| corrections 纠错台账 | **AgentRecall** | 结构化纠正（严重度/证据/生效验证）+ 双链回源，跨会话跨项目 |
| obsidian 桥梁 | **obsidian-mcp** | 直接文件系统读写 vault（免插件、免 key，`CUOHUATANG_VAULT_PATH` 指向） |

> 去重说明：errlore 与 AgentRecall 都治「二次犯错」，但分层不同——AgentRecall 管**记录**（每次纠正结构化入库），errlore 管**注入**（开工前把相关教训喂进上下文）。二者互补，合并为「记录 + 注入」一体。
> 淘汰说明：Mem0-MCP 已归档转云、jacksteamdev/obsidian-mcp-tools 已停更、claude-mem 仅服务 Claude Code —— 均不采用。

## 5. 工具规格（对外 13 个）

### 5.1 记忆 memory（源自 agentmemory）

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_memory_save` | content, title?, tags? | note_id, path | 记录一次会话事实/上下文，写入 01-流水账 并建索引 |
| `cm_memory_recall` | query, top_k=5 | note_id, title, snippet, score, method, path | 开工前召回相关记忆（混合检索） |
| `cm_memory_search` | query, top_k=10 | 同上列表 | 全库混合搜索（BM25 + 向量） |

### 5.2 总结 summarize（纯规则聚合 ★评审决策②）

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_summarize` | days=1, output_dir="04-经验总结" | path, summary_file | 把指定日期范围流水整理为结构化经验（**启发式/规则聚合**，不接 LLM） |
| `cm_summary_weekly` | scope="week" | path | 每周规则：流水+踩坑 → 方法论，写入经验总结 |

### 5.3 踩坑本 lessons（errlore 式）★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_lesson_add` | lesson, tags, model?, severity="medium", links? | note_id, path | 文件式记录一条教训（02-踩坑本），带标签、模型信任度与 **[[双链]] 回源** |
| `cm_lesson_inject` | query, top_k=3 | injected[], context_block | **开工前注入**：返回相关教训的现成上下文文本块（含模型标注），直接喂给 Agent 避免二次犯错 |

### 5.4 纠错台账 corrections（AgentRecall 式）★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_correction_log` | correction, evidence?, severity, model?, links? | note_id, path | 每次用户纠正即结构化记录（严重度/证据 + 双链），写 03-纠错台账 |
| `cm_correction_verify` | note_id, took_effect, note? | status | 追踪该纠正是否真的改变了 Agent 后续行为（回填状态） |
| `cm_correction_check` | query?, top_k=5 | 记录列表 | 开工前检查历史纠正+教训（合并 lessons 与 corrections 两库） |

### 5.5 Obsidian 桥梁 ★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_vault_init` | path? | vault_path, created_dirs | 初始化 vault 目录结构与 SQLite 索引（幂等） |
| `cm_obsidian_read` | path | content | 读取 vault 内 markdown（含 frontmatter 解析） |
| `cm_obsidian_write` | path, content, overwrite=False | path | 写入/新建 vault 内 markdown（安全：默认不覆盖） |

## 6. 存储格式

### 6.1 目录结构（`CUOHUATANG_VAULT_PATH`，默认 `~/.cuohuatang/vault` ★评审决策③：默认该路径且可编辑——环境变量/运行时参数均可覆盖）

```
vault/
├── 01-流水账/YYYY-MM-DD.md     ← memory 写入，按日期
├── 02-踩坑本/<slug>.md         ← lessons 写入（errlore 式文件踩坑本）
├── 03-纠错台账/<slug>.md       ← corrections 写入（AgentRecall 式台账）
└── 04-经验总结/<slug>.md       ← summarize 定期产物
```

### 6.2 markdown frontmatter 规范（Obsidian 原生支持）

```yaml
---
type: memory | lesson | correction | summary
category: 流水账 | 踩坑本 | 纠错台账 | 经验总结
status: active | verified | superseded
confidence: high | medium | low
created: 2026-10-09T22:40:00+08:00
updated: 2026-10-09T22:40:00+08:00
source: cuohuatang-mcp
tags: [qmt, rsi]
links: ["01-流水账/2026-10-09"]  # Obsidian 双链回源
model: gpt-5            # errlore 式：针对哪个模型的信任度
severity: high          # AgentRecall 式：纠正严重程度
evidence: "..."         # AgentRecall 式：证据/触发场景
---
# 标题
正文（用户可读、可改、可双链）
```

### 6.3 Obsidian 双链约定 ★评审决策④（已实现）

| 双链 | 格式 | 示例 |
|---|---|---|
| 踩坑本 → 流水账来源 | `[[01-流水账/YYYY-MM-DD]]` | `cm_lesson_add(..., links=["01-流水账/2026-10-09"])` |
| 纠错台账 → 关联教训 | `[[02-踩坑本/<slug>]]` | `cm_correction_log(..., links=["02-踩坑本/rsi-方向-ab12cd"])` |
| 经验总结 → 素材 | 同上 | summarize 产物在正文底部列出来源双链 |

`links` 参数写入 frontmatter 并在正文末尾渲染为 `- [[...]]` 列表，Obsidian 图谱直接可见；V0.2 的交接文档沿用同一约定（`05-交接/`）。

### 6.4 SQLite 索引（`CUOHUATANG_INDEX_PATH`，默认 `~/.cuohuatang/index.sqlite`，可重建）

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS notes USING fts5(
  note_id, title, content, tags, model, kind, updated_at,
  tokenize='unicode61'   -- 中文经 jieba 分词后入库
);
```

- 仅作检索加速；真相源永远是 markdown 文件
- `tags` 列存原样（不切词）：供聚类/过滤精确使用；全文命中走 `content` 列

### 6.5 混合检索（★评审决策①：向量 V0.1 就做）

| 层 | 实现 | 说明 |
|---|---|---|
| BM25 | SQLite FTS5（`bm25(notes)`） | 精确词命中排序 |
| 向量 | **TF-IDF + 余弦相似度**（jieba 分词，纯本地无外部模型） | 查询词子空间投影；对 BM25 查不到的相关文档兜底 |
| 融合 | 归一化加权 0.5/0.5，按融合分排序 | 结果带 `method: bm25/hybrid/vector` 字段，可审计 |

- `search(query, hybrid=True)` 默认混合；`hybrid=False` 退回纯 BM25
- 中文分词：**jieba + FTS5(unicode61)**（纯 unicode61 连续中文无法分词、trigram 对 2 字词失效，均实测不可用）
- 向量为每文档 TF-IDF 加权词袋，缓存随索引 mtime 失效

## 7. 配置与接入（各 Agent 同一份 JSON）

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

| Agent | 接入位置 |
|---|---|
| Claude Code | `.mcp.json`（项目）或 `claude mcp add cuohuatang -- uvx cuohuatang-mcp` |
| Cursor | Settings → MCP |
| OpenClaw / Hermes | 各自 MCP 插件配置 |
| Codex / Cline / Aider 等 | 任意支持 MCP 的客户端，同一段 JSON |

环境变量（均可编辑）：`CUOHUATANG_HOME`（默认 `~/.cuohuatang`）、`CUOHUATANG_VAULT_PATH`、`CUOHUATANG_INDEX_PATH`。

## 8. 免 key 设计

| 能力 | 默认（零 key，V0.1） | 可选增强（V0.2+，仍免云 key） |
|---|---|---|
| 召回 | **BM25 + TF-IDF 向量混合** | 本地 BGE-M3 embedder（仿 m3-memory，`127.0.0.1:8082`） |
| 压缩/总结 | **纯规则聚合**（★决策②） | 宿主 Agent 自带 LLM，或本地 Ollama（需用户明确启用） |
| 存储 | 本地文件 + SQLite | 同上 |

不强制任何账号、API key、云服务；数据不出本机。

## 9. 数据生命周期与隐私

- 写入：全部经 `cm_obsidian_write` 统一路径校验（禁止越出 vault 根目录，防路径穿越）
- 读取：vault 内 markdown 只读加载
- 重建：`index.sqlite` 可随时删除重建，不丢任何数据（`rebuild_index()` 全量重建）
- 隐私：默认零网络调用；除非用户显式允许，不上传任何内容

## 10. 测试计划（已实现）

| 层 | 用例 | 状态 |
|---|---|---|
| storage | vault 初始化幂等；FTS5 建表/写入/检索；路径穿越防护；**混合检索向量兜底**；索引重建 | ✅ |
| memory | save→recall 闭环；中文关键词检索 | ✅ |
| lessons/corrections | add→inject / log→check 闭环；frontmatter 字段完整性；**双链落盘** | ✅ |
| obsidian | read/write 往返；overwrite=False 拒绝覆盖 | ✅ |
| server | 13 个工具全部注册成功 | ✅ |

V0.1 共 **9 项单元测试全过** + 端到端 stdio 冒烟（13 工具注册、记忆/踩坑/纠错/总结全链路、混合检索、双链、markdown 落盘到 4 个 Obsidian 目录）。

## 11. 发布记录（对齐 mmczok 流程：先拉后改，改完推，发版前请示）

1. ✅ 评审本设计 + 骨架（用户确认）
2. ✅ 实现全部模块（记忆/教训/台账/总结/桥梁 + 向量/双链）→ 本地 9 项测试全过 + 端到端冒烟
3. ✅ **2026-10-09 推送 GitHub 公开仓库 `cuohuatang/cuohuatang-mcp`，打 tag v0.1.0**
4. ⏳ V0.2（handoff + skillcraft，18 工具）已实现于 feature 分支，**待用户指示后发布**
5. 可选：发布 PyPI（`pip install cuohuatang-mcp` / `uvx cuohuatang-mcp`）

## 12. 实施记录（V0.1）

| 项 | 结论 |
|---|---|
| MCP SDK | 采用 **mcp 2.x（MCPServer API）**，非 v1 FastMCP（v1 已更名迁移；`mcp>=2.0.0`） |
| 中文检索 | **jieba 分词 + FTS5(unicode61)**：实测 `QMT`/`报错`/`QMT 报错`/`行情` 全部命中（纯 unicode61 连续中文无法分词，trigram 对 2 字词失效，均不可用） |
| 向量检索 | **TF-IDF + 余弦**（查询词子空间投影）；hybrid 归一化加权融合；`method` 字段可审计 |
| tags 存储 | tags 列保持原样不切词（聚类/过滤精确），全文命中走 content 列 |
| 双链约定 | `links` 参数 → frontmatter + 正文 `[[...]]` 渲染（踩坑/纠错已实现） |
| 空查询 | `cm_correction_check` 空查询走 `recent()`（按更新时间倒序），不再传 FTS 通配符 |
| 验证 | 9 项单元测试全过 + 端到端 stdio 冒烟（13 工具、混合检索、双链、4 目录落盘） |

## 13. 已确认决策（用户评审通过）

| # | 决策 | 落地 |
|---|---|---|
| ① | 向量检索 V0.1 就做 | ✅ hybrid = BM25 + TF-IDF 向量（第 6.5 节） |
| ② | `cm_summarize` 纯规则聚合 | ✅ 不接外部 LLM（第 5.2 节） |
| ③ | vault 默认 `~/.cuohuatang/vault` 且可编辑 | ✅ 环境变量/运行时参数可覆盖（第 6.1、7 节） |
| ④ | 交接/踩坑加 Obsidian 双链约定 | ✅ 踩坑/纠错已实现（第 6.3 节）；交接随 V0.2 沿用 |

## 附录 A：V0.2 规划（已实现，待发布）

> 已完整实现于 `feature/v0.2-handoff-skillcraft` 分支并验证（11 项测试全过、18 工具端到端冒烟），**未并入 V0.1 发布**，等用户指示后合并发布 v0.2.0。

- **⑥ 会话交接（session-handoff 式）**：`cm_handoff_create/list/resume`，六段式交接文档写入 `05-交接`；有未答问题先转问用户，否则新 Agent 直接接手。
- **⑦ 技能沉淀（session-to-skill / ritual 式）**：`cm_skill_suggest` 按主题聚类，同一主题≥2 次自动提示"需要我把『×××』生成一个 skill 吗？"；`cm_skill_propose` 生成 SKILL.md 草稿（只展示不写盘，推荐跨 Agent 路径 `~/.agents/skills/<name>/SKILL.md`）。
- 注：用户点名的 "ritual" 在 squidllee/skills 仓库中无独立同名技能，"挖重复工作流 + 自动提示生成 skill" 对应 **session-to-skill**（已完整读取并按其精华实现）。
