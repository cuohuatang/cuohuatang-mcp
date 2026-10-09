# cuohuatang-mcp 设计文档（v0.1 设计与骨架）

> 状态：设计定稿 + 骨架已生成，待评审后迭代补全实现
> 技术栈：Python（FastMCP / `mcp>=2.0`）
> 目标仓库：`cuohuatang/cuohuatang-mcp`（GitHub，私有迭代 → 稳定后发版）
> 许可：MIT

---

## 1. 定位

一个**免费、免 API key、纯本地**的一体化 MCP 服务器：把 Agent 的「自动记忆 + 自动总结 + 自动纠错（踩坑本/纠错台账）+ Obsidian 嫁接」合并为**一套代码、一组 `cm_` 工具**，装一次即可接入 Claude Code / Cursor / OpenClaw / Hermes / Codex 等所有 MCP 客户端。

核心思想：**不要让每个工具各存各的**。所有记忆、教训、纠正最终都写入 Obsidian 兼容的 markdown 文件，Obsidian 作为唯一真相源（Single Source of Truth）；任何 Agent 通过本服务器读写同一个 vault，等于共用一个大脑。

## 2. 设计原则

| # | 原则 | 说明 |
|---|---|---|
| P1 | 合并不包装 | 不嵌套启动 agentmemory / AgentRecall / obsidian-mcp 进程（stdio 嵌套是坑），而是**取各家功能设计，一套代码重写合并** |
| P2 | 免 key 优先 | 默认零 API key：BM25（SQLite FTS5）召回、启发式压缩；本地 embedding / LLM 压缩为可选增强 |
| P3 | Obsidian 唯一真相源 | 全部数据为 markdown（带 frontmatter），可直接用 Obsidian 打开；SQLite 仅作检索索引，可随时重建 |
| P4 | 文件式优先 | 参考 errlore「文件式、无服务器」：数据即文件，用户看得见、改得动、搜得到 |
| P5 | 跨 Agent 通用 | 同一份 `mcpServers` JSON 粘贴到每个 Agent 即可，不做任何单工具绑定 |

## 3. 总体架构

```
      Claude Code / Cursor / OpenClaw / Hermes / Codex / ...
                     │  （全部走 MCP stdio）
                     ▼
          ┌────────────────────────────┐
          │      cuohuatang-mcp        │  ← 本服务器（FastMCP）
          │  ┌────────┬───────┬──────┐ │
          │  │ memory │ lessons│corr │ │  ① 自动记忆  ② 踩坑本(errlore式)
          │  │ (agent │ (errlore│ect │ │  ③ 纠错台账  ④ 自动总结
          │  │memory式)│  式)  │(Recall│ ⑤ Obsidian 桥梁
          │  │  └──┬──┴──┬───┴─┬─┘  │
          │  └─────┼─────┼─────┼────┘
          │   summarize ┘     │
          └────────┼──────────┼────────┘
                   ▼          ▼
        ┌────────────────┐   ┌──────────────────┐
        │ ~/.cuohuatang/ │   │ index.sqlite     │
        │   vault/       │   │ FTS5(BM25) 索引  │
        │  (markdown)    │   │ （可重建）        │
        └────────────────┘   └──────────────────┘
                   │
                   ▼
        Obsidian 打开 vault 即见即改（双链/搜索/标签）
```

## 4. 模块来源对照（去重合并结果）

| cuohuatang-mcp 模块 | 功能来源 | 合并方式 |
|---|---|---|
| memory 自动记忆 | agentmemory | 会话记录 + 上下文召回（BM25+向量混合，v0 先 BM25） |
| summarize 自动总结 | agentmemory `mem::compress` | 会话压缩 + 每周定期整理 |
| lessons 踩坑本 | **errlore** | 文件式教训 + 标签 + **按模型信任度**，开工前自动注入已知错误 |
| corrections 纠错台账 | **AgentRecall** | 结构化纠正（严重度/证据/生效验证），跨会话跨项目 |
| obsidian 桥梁 | **obsidian-mcp** | 直接文件系统读写 vault（免插件、免 key，`CUOHUATANG_VAULT_PATH` 指向） |

> 去重说明：errlore 与 AgentRecall 都治「二次犯错」，但分层不同——AgentRecall 管**记录**（每次纠正结构化入库），errlore 管**注入**（开工前把相关教训喂进上下文）。二者互补，合并为「记录 + 注入」一体。

## 5. 工具规格（对外 13 个）

### 5.1 记忆 memory（源自 agentmemory）

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_memory_save` | content, title?, tags? | note_id, path | 记录一次会话事实/上下文，写入 01-流水账 并建索引 |
| `cm_memory_recall` | query, top_k=5 | note_id, title, snippet, score, path | 开工前召回相关记忆 |
| `cm_memory_search` | query, filters?, top_k=10 | 同上列表 | 全库混合搜索（v0：FTS5 BM25） |

### 5.2 总结 summarize

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_summarize` | days=1, output_dir="04-经验总结" | path, summary_file | 把指定日期范围流水整理为结构化经验（v0 为启发式聚合，LLM 可选增强） |
| `cm_summary_weekly` | scope="week" | path | 每周规则：流水+踩坑 → 方法论，写入经验总结 |

### 5.3 踩坑本 lessons（errlore 式）★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_lesson_add` | lesson, tags, model?, severity="medium" | note_id, path | 文件式记录一条教训（02-踩坑本），带标签与模型信任度 |
| `cm_lesson_inject` | query, top_k=3 | injected[], context_block | **开工前注入**：返回相关教训的现成上下文文本块（含模型标注），直接喂给 Agent 避免二次犯错 |

### 5.4 纠错台账 corrections（AgentRecall 式）★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_correction_log` | correction, evidence?, severity, model? | note_id, path | 每次用户纠正即结构化记录（严重度/证据），写 03-纠错台账 |
| `cm_correction_verify` | note_id, took_effect, note? | status | 追踪该纠正是否真的改变了 Agent 后续行为 |
| `cm_correction_check` | query?, top_k=5 | 记录列表 | 开工前检查历史纠正+教训（合并 lessons 与 corrections 两库） |

### 5.5 Obsidian 桥梁 ★ 用户点名

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_vault_init` | path? | vault_path, created_dirs | 初始化 vault 目录结构与 SQLite 索引（幂等） |
| `cm_obsidian_read` | path, vault_relative=True | content | 读取 vault 内 markdown（含 frontmatter 解析） |
| `cm_obsidian_write` | path, content, overwrite=False | path | 写入/新建 vault 内 markdown（安全：默认不覆盖） |

## 6. 存储格式

### 6.1 目录结构（`CUOHUATANG_VAULT_PATH`，默认 `~/.cuohuatang/vault`）

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
model: gpt-5            # errlore 式：针对哪个模型的信任度
severity: high          # AgentRecall 式：纠正严重程度
evidence: "..."         # AgentRecall 式：证据/触发场景
---
# 标题
正文（用户可读、可改、可双链）
```

### 6.3 SQLite 索引（`~/.cuohuatang/index.sqlite`，可重建）

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS notes USING fts5(
  note_id, title, content, tags, model, kind, updated_at,
  tokenize='unicode61'   -- 中文按 unicode 切分 + 前缀匹配
);
```

- 仅作检索加速；真相源永远是 markdown 文件
- `cm_vault_init` 提供 `--rebuild-index`（从 markdown 全量重建）

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

## 8. 免 key 设计

| 能力 | 默认（零 key） | 可选增强（仍免云 key） |
|---|---|---|
| 召回 | SQLite FTS5（BM25，unicode61 中文友好） | 本地 BGE-M3 embedder（仿 m3-memory，`127.0.0.1:8082`） |
| 压缩/总结 | 启发式：标题/文件/叙事聚合 | 宿主 Agent 自带 LLM，或本地 Ollama |
| 存储 | 本地文件 + SQLite | 同上 |

不强制任何账号、API key、云服务；数据不出本机。

## 9. 数据生命周期与隐私

- 写入：全部经 `cm_obsidian_write` 统一路径校验（禁止越出 vault 根目录，防路径穿越）
- 读取：vault 内 markdown 只读加载
- 重建：`index.sqlite` 可随时删除重建，不丢任何数据
- 隐私：默认零网络调用；除非用户显式允许，不上传任何内容

## 10. 测试计划（骨架已含基础用例）

| 层 | 用例 |
|---|---|
| storage | vault 初始化幂等；FTS5 建表/写入/检索；路径穿越防护 |
| memory | save→recall 闭环；中文关键词检索 |
| lessons/corrections | add→inject / log→check 闭环；frontmatter 字段完整性 |
| obsidian | read/write 往返；overwrite=False 拒绝覆盖 |
| server | 13 个工具全部注册成功 |

## 11. 发布计划（对齐 mmczok 流程）

1. 评审本设计 + 骨架（当前阶段）
2. 补全各模块实现（内存/教训/台账/总结/桥梁）→ 本地跑通
3. GitHub 私有仓 `cuohuatang/cuohuatang-mcp`，固定流程：先拉后改，改完推
4. 迭代稳定后打 Tag 发版（发版前向用户请示，铁律⑨）
5. 可选：发布 PyPI（`pip install cuohuatang-mcp` / `uvx cuohuatang-mcp`）

## 12. 实施记录（v0.1 + v0.2 骨架已完成）

| 项 | 结论 |
|---|---|
| MCP SDK | 采用 **mcp 2.x（MCPServer API）**，非 v1 FastMCP（v1 已更名迁移；`mcp>=2.0.0`） |
| 中文检索 | 采用 **jieba 分词 + FTS5(unicode61)**：索引与查询统一切词。实测 `QMT`/`报错`/`QMT 报错`/`行情` 全部命中（纯 unicode61 连续中文无法分词，trigram 对 2 字词失效，均不可用） |
| tags 存储 | tags 列保持原样不切词（聚类/过滤精确），全文命中走 content 列 |
| 空查询 | `cm_correction_check` 空查询走 `recent()`（按更新时间倒序），不再传 FTS 通配符 |
| 验证 | **11 个单元测试全过** + 端到端 stdio 冒烟（**18 工具**注册；记忆/踩坑/纠错/总结/交接/技能沉淀全链路；交接未答问题转交；重复工作流自动提示；markdown 落盘到 5 个 Obsidian 目录） |

## 13. v0.2 增量：会话交接 + 技能沉淀（已并入骨架）

> 来源：GitHub `squidllee/skills`（100+ skills 仓库）中的 **session-handoff** 与 **session-to-skill** 精华。注：用户点名的 "ritual" 在该仓库及公开检索中均无独立同名技能；"跨 Agent 挖重复工作流 + 自动提示生成 skill" 的功能对应 **session-to-skill**，已按此实现。

### 13.1 ⑥ 会话交接 handoff（session-handoff 式）★ 用户补充①

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_handoff_create` | task_overview, current_state, important_discoveries?, next_steps?, context_to_preserve?, unanswered_question?, from_agent?, to_agent? | note_id, path | 六段式交接文档写入 05-交接，跨 Agent 续命 |
| `cm_handoff_list` | top_k=10 | 交接列表 | 列出最近交接 |
| `cm_handoff_resume` | handoff_id | must_answer/question/instruction | 新 Agent 接手：有未答问题先转问，否则直接开干（不问许可、不重复解释） |

精华规则移植：①六段式结构（任务概览/当前状态/重要发现/下一步/需保留上下文/未回答问题），空节不编造填充；②有未答问题必须转问用户、不默认；③无未答问题立刻接手干活。不依赖 entire CLI，以 cuohuatang 自身数据驱动；可选适配 entire 格式留待迭代。

### 13.2 ⑦ 技能沉淀 skillcraft（session-to-skill / ritual 式）★ 用户补充②

| 工具 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `cm_skill_suggest` | top_k=30 | suggestions[], prompt | 扫描记忆/踩坑/纠错/交接按 tags 聚类；主题出现≥2 次 → 自动提示"需要我把『×××』生成一个 skill 吗？" |
| `cm_skill_propose` | target, tags? | skill_name, SKILL.md 草稿, 推荐安装路径 | 生成 SKILL.md 草稿（只展示不写盘）；推荐跨 Agent 路径 `~/.agents/skills/<name>/SKILL.md` |

精华规则移植：①先识别可复用行为、用证据挖掘而非机械转换；②只沉淀可复用工作流与规则，不含一次性内容/密钥/隐私；③草稿先展示，写文件必须用户确认；④推荐跨 Agent 全局安装路径。

### 13.3 自动提示机制的触发时机（写入 AGENT 一体化提示词）

```
每次会话结束时：cm_summarize 沉淀要点 → cm_skill_suggest 检查重复工作流
→ 若命中（同一主题≥2次），自动向用户提问："需要我把『×××』生成一个 skill 吗？"
```

## 14. 待办（评审时确认）

- [ ] 向量检索增强是否 v0.1 就做（默认 v0.1 只做 BM25）
- [ ] `cm_summarize` 的 LLM 增强是否接宿主 Agent 回调，还是纯规则聚合
- [ ] vault 路径默认值：`~/.cuohuatang/vault` 还是直接指向用户现有 Obsidian 库
- [ ] 是否提供 Obsidian 模板/双链约定（如 `[[02-踩坑本/xxx]]`）
