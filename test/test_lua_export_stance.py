"""验证导出链路不会丢掉姿态配置

覆盖两个导出入口：
- 导出 GHUB 脚本 → generate_auto_recognize_script
- 导出 dofile 脚本 → generate_dofile_files（含 pubg_config.lua 重新生成）

重点：pubg_config.lua 是从基础脚本重新提取的，若基础脚本的 userInfo
缺 stance 段，姿态识别会被静默抹掉。这里同时验证兜底注入能补上。

可直接运行：python test/test_lua_export_stance.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pubg_gun_control.lua_generator import (  # noqa: E402
    generate_auto_recognize_script,
    generate_config_only,
    generate_dofile_files,
)

BASE_LUA = ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua"

_STANCE_BLOCK = (
    '\tstance = {\n'
    '\t\tenabled = true,\n'
    '\t\tbase = "crouch",\n'
    '\t},'
)


def _strip_stance(text: str) -> str:
    """模拟"尚未同步姿态配置"的旧版基础脚本"""
    return text.replace(_STANCE_BLOCK, "")


def test_base_script_has_stance() -> None:
    text = BASE_LUA.read_text(encoding="utf-8")
    assert "function pubg.readStance" in text, "基础脚本缺少 readStance"
    assert "pubg.currentStance = pubg.readStance()" in text, "基础脚本未刷新姿态"
    assert "stance = {" in text, "基础脚本 userInfo 缺少 stance"


def test_export_ghub_script_keeps_stance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "auto_recognize_ghub.lua"
        generate_auto_recognize_script(
            str(BASE_LUA), output_path=str(out),
            rec_path=str(ROOT / "pubg_rec.lua"),
        )
        text = out.read_text(encoding="utf-8")
        assert "function pubg.readStance" in text
        assert 'rec_stance = "stand"' in text


def test_export_dofile_keeps_stance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        wrapper = Path(tmp) / "ghub_dofile_wrapper.lua"
        config = Path(tmp) / "pubg_config.lua"
        generate_dofile_files(
            str(BASE_LUA), config_output=str(config), wrapper_output=str(wrapper),
            rec_path=str(ROOT / "pubg_rec.lua"),
        )
        wrapper_text = wrapper.read_text(encoding="utf-8")
        config_text = config.read_text(encoding="utf-8")

        assert "function pubg.readStance" in wrapper_text, "wrapper 丢失姿态逻辑"
        assert 'rec_stance = "stand"' in wrapper_text, "wrapper 缺 rec_stance 声明"
        assert "stance = {" in config_text, "pubg_config.lua 丢失 stance"


def test_config_only_injects_stance_when_source_is_old() -> None:
    """基础脚本是旧版（无 stance）时，生成配置要能自动补齐"""
    with tempfile.TemporaryDirectory() as tmp:
        old_source = Path(tmp) / "old_base.lua"
        old_source.write_text(
            _strip_stance(BASE_LUA.read_text(encoding="utf-8")), encoding="utf-8"
        )
        assert "stance = {" not in old_source.read_text(encoding="utf-8")

        config = Path(tmp) / "pubg_config.lua"
        generate_config_only(str(old_source), config_output=str(config))
        text = config.read_text(encoding="utf-8")
        assert "stance = {" in text, "旧基础脚本导出时未补齐 stance"
        assert 'base = "' in text


def test_injected_stance_is_valid_lua_shape() -> None:
    """补进去的段必须出现在 userInfo 块内部（在收尾 } 之前）"""
    with tempfile.TemporaryDirectory() as tmp:
        old_source = Path(tmp) / "old_base.lua"
        old_source.write_text(
            _strip_stance(BASE_LUA.read_text(encoding="utf-8")), encoding="utf-8"
        )
        config = Path(tmp) / "pubg_config.lua"
        generate_config_only(str(old_source), config_output=str(config))
        text = config.read_text(encoding="utf-8")

        ui_start = text.index("userInfo = {")
        # 找到 userInfo 块的收尾大括号（下一个顶层 "}"）
        ui_end = text.index("\n}", ui_start)
        block = text[ui_start:ui_end]
        assert "stance = {" in block, "stance 被插到了 userInfo 块外面"


def main() -> int:
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {test.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
