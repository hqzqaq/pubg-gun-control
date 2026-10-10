"""pytest 会话级fixture

解决 CI 与本地的行为差异：`pubg_config.lua` 是运行时生成的产物（已被.gitignore
排除），干净检出的 CI 上并不存在，导致依赖它的测试全部报
`BallisticParseError: 文件不存在`。

这里在测试会话开始时，从**已跟踪的基础脚本**临时生成一份
`pubg_config.lua`，让测试在任何环境下都能自给自足。

注意：仅在文件缺失时生成，绝不覆盖用户本地的真实配置。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 基础脚本（已纳入版本控制）与生成产物
BASE_LUA = PROJECT_ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua"
CONFIG_LUA = PROJECT_ROOT / "pubg_config.lua"


def pytest_sessionstart(session: pytest.Session) -> None:
    """会话启动时确保 pubg_config.lua 存在。"""
    if CONFIG_LUA.exists():
        # 本地已有真实配置（开发/调试场景），保持原样不动
        return

    if not BASE_LUA.exists():
        raise pytest.UsageError(
            f"基础脚本缺失，无法生成测试用配置：{BASE_LUA}\n"
            "该文件应已纳入版本控制，请检查仓库是否完整。"
        )

    from pubg_gun_control.lua_generator import generate_config_only

    generate_config_only(str(BASE_LUA), str(CONFIG_LUA))