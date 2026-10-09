"""⑦ 技能沉淀模块（源自 squidllee/session-to-skill 精华，即"ritual 式"）：

跨 Agent 挖掘重复工作流 → 自动提示生成 skill。

精华移植（不依赖 entire CLI，用 cuohuatang 自身数据驱动）：
- 先识别可复用行为，用证据（记忆/踩坑/纠错/交接记录）而非机械转换
- 只沉淀可复用工作流与规则，不含一次性内容、密钥、隐私
- 草稿先展示、不直接写文件；写文件必须用户确认；推荐跨 Agent 路径 ~/.agents/skills/<name>/SKILL.md
- 自动提示机制：检测到同一主题重复出现时，主动问"需要我把×××生成一个 skill 吗？"
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import date
from typing import Any

from ..storage import vault

_SUGGEST_MIN_REPEAT = 2  # 同一主题出现≥2次即判定为重复工作流


def suggest(top_k: int = 30) -> dict[str, Any]:
    """扫描记忆/踩坑/纠错/交接，按 tags 聚类挖掘重复工作流，返回自动提示文案。"""
    hits = vault.recent(top_k=top_k)
    tag_counter: Counter = Counter()
    for h in hits:
        for tag in h.get("tags", []):
            tag_counter[tag] += 1
    repeats = sorted(
        ((tag, n) for tag, n in tag_counter.items() if n >= _SUGGEST_MIN_REPEAT),
        key=lambda x: -x[1],
    )
    suggestions = [
        {"workflow": tag, "occurrences": n, "evidence_kinds": sorted({h["kind"] for h in hits if tag in h.get("tags", [])})}
        for tag, n in repeats[:5]
    ]
    if not suggestions:
        return {"suggestions": [], "prompt": "（暂无重复工作流，继续积累中）"}
    top = suggestions[0]
    prompt = f"检测到重复工作流『{top['workflow']}』（出现 {top['occurrences']} 次），需要我把『{top['workflow']}』生成一个 skill 吗？"
    return {"suggestions": suggestions, "prompt": prompt}


def propose(target: str, tags: list[str] | None = None) -> dict[str, Any]:
    """把重复工作流沉淀为 SKILL.md 草稿（只展示不写文件）。"""
    name = _to_kebab(target)
    skill_name = f"{name}-skill"
    description = f"Use when the user wants to {target}（重复工作流自动沉淀）。"
    draft = f"""---
name: {skill_name}
description: {description}
---

# {skill_name}

## 目的
把重复工作流「{target}」固化为可复用技能，避免每次从头开始、重复踩坑。

## 规则
1. 开工前先调用 cuohuatang-mcp 的 cm_memory_recall / cm_correction_check 召回历史与踩坑记录。
2. 只复用本流程已验证的步骤；遇到新情况先记录（cm_lesson_add）再决定是否纳入。
3. 不泄露密钥、隐私与一次性细节。

## 工作流
1. 确认本次输入与成功标准。
2. 按既定步骤执行（待填充：由 cuohuatang 从历史记录自动提炼）。
3. 执行后 cm_summarize 沉淀要点，cm_correction_log 记录任何纠正。

## 验证
- 产物与成功标准逐项对照。
- 新教训写入踩坑本后，下次 cm_lesson_inject 自动注入。

## 失败处理
- 遇到未收录的新情况：记录教训，向用户确认是否扩展本技能。
"""
    return {
        "skill_name": skill_name,
        "target": target,
        "source_tags": tags or [],
        "sk_md_draft": draft,
        "destination_recommended": f"~/.agents/skills/{skill_name}/SKILL.md",
        "note": "草稿仅展示，未写盘；确认后按你选择的路径安装（写盘前会再次征求同意）。",
    }


def _to_kebab(text: str) -> str:
    import re

    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-")
    return (s[:40] or f"skill-{uuid.uuid4().hex[:6]}").lower()
