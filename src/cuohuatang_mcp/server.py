"""cuohuatang-mcp 服务器入口：MCPServer 注册全部 13 个 cm_ 工具（V0.1）。"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import __version__
from .modules import corrections, lessons, memory, obsidian, summarize

mcp = MCPServer(
    name="cuohuatang-mcp",
    instructions=(
        "一体化记忆系统：自动记忆、自动总结、踩坑本(errlore式)、纠错台账(AgentRecall式)、"
        "Obsidian 嫁接。全部本地存储、免 API key；混合检索（BM25 + TF-IDF 向量）。"
        "开工前建议先 cm_memory_recall + cm_correction_check。"
    ),
)


# ---------- ① 记忆 ----------
@mcp.tool()
def cm_memory_save(content: str, title: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """记录一次会话事实/上下文到流水账（自动记忆）。"""
    return memory.save(content, title, tags)


@mcp.tool()
def cm_memory_recall(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """开工前召回相关历史记忆。"""
    return memory.recall(query, top_k)


@mcp.tool()
def cm_memory_search(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """全库搜索记忆。"""
    return memory.search(query, top_k)


# ---------- ② 总结 ----------
@mcp.tool()
def cm_summarize(days: int = 1, output_dir: str = "04-经验总结") -> dict[str, Any]:
    """把最近 N 天流水整理为结构化经验。"""
    return summarize.summarize(days, output_dir)


@mcp.tool()
def cm_summary_weekly(scope: str = "week") -> dict[str, Any]:
    """每周自动总结：流水+踩坑+纠错 → 方法论。"""
    return summarize.weekly(scope)


# ---------- ③ 踩坑本（errlore 式）----------
@mcp.tool()
def cm_lesson_add(lesson: str, tags: list[str] | None = None, model: str | None = None, severity: str = "medium", links: list[str] | None = None) -> dict[str, Any]:
    """文件式记录一条教训到踩坑本（专治二次犯错；links 为 Obsidian 双链回源）。"""
    return lessons.add(lesson, tags, model, severity, links)


@mcp.tool()
def cm_lesson_inject(query: str, top_k: int = 3) -> dict[str, Any]:
    """开工前注入相关已知教训（含模型信任度标注）。"""
    return lessons.inject(query, top_k)


# ---------- ④ 纠错台账（AgentRecall 式）----------
@mcp.tool()
def cm_correction_log(correction: str, evidence: str | None = None, severity: str = "medium", model: str | None = None, links: list[str] | None = None) -> dict[str, Any]:
    """记录一次用户纠正（严重度/证据），跨会话保留（links 为 Obsidian 双链回源）。"""
    return corrections.log(correction, evidence, severity, model, links)


@mcp.tool()
def cm_correction_verify(note_id: str, took_effect: bool, note: str | None = None) -> dict[str, Any]:
    """标记纠正是否真正生效。"""
    return corrections.verify(note_id, took_effect, note)


@mcp.tool()
def cm_correction_check(query: str | None = None, top_k: int = 5) -> list[dict[str, Any]]:
    """开工前检查历史纠正+教训。"""
    return corrections.check(query, top_k)


# ---------- ⑤ Obsidian 桥梁 ----------
@mcp.tool()
def cm_vault_init(path: str | None = None) -> dict[str, Any]:
    """初始化 vault 目录与索引（幂等）。"""
    return obsidian.vault_init(path)


@mcp.tool()
def cm_obsidian_read(path: str) -> dict[str, Any]:
    """读取 vault 内 markdown（含 frontmatter）。"""
    return obsidian.read(path)


@mcp.tool()
def cm_obsidian_write(path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
    """写入 vault 内 markdown（默认不覆盖）。"""
    return obsidian.write(path, content, overwrite)


def main() -> None:
    """CLI 入口：mcp.run() 走 stdio。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
