"""技能沉淀模块测试：重复工作流挖掘 + 自动提示 + SKILL.md 草稿。"""

from __future__ import annotations

from pathlib import Path

import pytest

from cuohuatang_mcp import config
from cuohuatang_mcp.modules import skillcraft
from cuohuatang_mcp.storage import vault


@pytest.fixture()
def tmp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault, "VAULT_PATH", tmp_path / "vault")
    monkeypatch.setattr(config, "VAULT_PATH", tmp_path / "vault")
    monkeypatch.setattr(vault, "INDEX_PATH", tmp_path / "index.sqlite")
    monkeypatch.setattr(config, "INDEX_PATH", tmp_path / "index.sqlite")
    vault.init_vault()


def test_suggest_detects_repeated_workflow(tmp_env) -> None:
    for i in range(3):
        vault.write_note(
            f"{config.VAULT_DIRS['memory']}/2026-10-0{i+1}.md",
            f"发布小红书笔记 {i}",
            {"title": f"小红书发布 {i}", "type": "memory", "tags": ["小红书发布", "内容"]},
        )
    result = skillcraft.suggest(top_k=30)
    assert result["suggestions"]
    assert result["suggestions"][0]["workflow"] == "小红书发布"
    assert "生成一个 skill 吗" in result["prompt"]


def test_propose_generates_draft_without_writing(tmp_env) -> None:
    result = skillcraft.propose("发布小红书笔记", tags=["小红书发布"])
    assert result["skill_name"].startswith("发布小红书笔记")
    assert result["sk_md_draft"].startswith("---")
    assert "name:" in result["sk_md_draft"]
    assert "~/.agents/skills/" in result["destination_recommended"]
    assert "未写盘" in result["note"]
