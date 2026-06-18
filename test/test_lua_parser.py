"""
lua 解析器测试

验证 LuaBallisticParser 能正确解析 GHUB lua 脚本，
并能在序列化后保持数据一致。

@author huquanzhi
@since 2026-06-18 19:35
@version 1.0
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pubg_gun_control.lua_parser import LuaBallisticParser, BallisticParseError  # noqa: E402


LUA_FILE = PROJECT_ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua"


def test_parse_lua() -> None:
    """测试解析现有 lua 文件"""
    parser = LuaBallisticParser()
    config = parser.parse(LUA_FILE)

    # 校验弹药组数量
    expected_ammo = {"7.62", "5.56", ".45", "9mm"}
    assert set(config.ammo_groups.keys()) == expected_ammo, (
        f"弹药组不匹配: {set(config.ammo_groups.keys())} vs {expected_ammo}"
    )

    # 校验总枪数
    total_guns = sum(len(g) for g in config.ammo_groups.values())
    print(f"  解析到 {total_guns} 把枪，分布在 {len(config.ammo_groups)} 个弹药组")
    assert total_guns >= 15, f"枪数过少: {total_guns}"

    # 校验附件
    assert "muzzle" in config.attachment_config
    assert "grip" in config.attachment_config
    assert "stock" in config.attachment_config
    print(
        f"  配件配置: muzzle={len(config.attachment_config['muzzle'].items)} "
        f"grip={len(config.attachment_config['grip'].items)} "
        f"stock={len(config.attachment_config['stock'].items)}"
    )

    # 校验特定枪的系数
    m762 = config.find_gun("Beryl M762")
    assert m762 is not None, "未找到 Beryl M762"
    assert m762.mode == 1
    assert abs(m762.coef - 8.65) < 0.01
    print(f"  M762 校验: mode={m762.mode}, coef={m762.coef}")

    # 校验 gunNoStock
    assert config.gun_no_stock.get("Beryl M762") is True
    assert config.gun_no_stock.get("UMP45") is True
    print(f"  gunNoStock 枪械数: {len(config.gun_no_stock)}")


def test_round_trip() -> None:
    """测试 parse → 修改 → serialize → parse 后数据一致"""
    parser = LuaBallisticParser()
    config = parser.parse(LUA_FILE)

    # 修改 M762 系数
    m762 = config.find_gun("Beryl M762")
    assert m762 is not None
    original_coef = m762.coef
    m762.coef = 9.99  # 测试值

    # 序列化到临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lua", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(LUA_FILE.read_text(encoding="utf-8"))
        tmp_path = Path(tmp.name)

    try:
        parser.serialize(config, tmp_path, backup=False)
        # 再解析
        config2 = parser.parse(tmp_path)
        m762_2 = config2.find_gun("Beryl M762")
        assert m762_2 is not None
        assert abs(m762_2.coef - 9.99) < 0.001, (
            f"round-trip 失败: 期望 9.99, 实际 {m762_2.coef}"
        )
        print(f"  Round-trip 校验: M762 coef {original_coef} -> 9.99 -> {m762_2.coef} OK")
    finally:
        tmp_path.unlink(missing_ok=True)


def test_backup() -> None:
    """测试备份功能"""
    parser = LuaBallisticParser()
    config = parser.parse(LUA_FILE)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lua", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(LUA_FILE.read_text(encoding="utf-8"))
        tmp_path = Path(tmp.name)

    try:
        parser.serialize(config, tmp_path, backup=True)
        bak_path = tmp_path.with_suffix(tmp_path.suffix + ".bak")
        assert bak_path.exists(), "备份文件未生成"
        # 第一次备份内容应与原文件一致
        bak_content = bak_path.read_text(encoding="utf-8")
        original = LUA_FILE.read_text(encoding="utf-8")
        assert bak_content == original, "备份内容与原文件不一致"
        print(f"  备份文件已生成: {bak_path}")
    finally:
        bak_path = tmp_path.with_suffix(tmp_path.suffix + ".bak")
        tmp_path.unlink(missing_ok=True)
        bak_path.unlink(missing_ok=True)


def test_parse_error() -> None:
    """测试解析错误处理"""
    parser = LuaBallisticParser()
    try:
        parser.parse("nonexistent_file_12345.lua")
        assert False, "应抛异常"
    except BallisticParseError as exc:
        print(f"  错误处理 OK: {exc}")
        assert "不存在" in str(exc)


def main() -> int:
    print("=" * 60)
    print("lua 解析器测试")
    print("=" * 60)

    tests = [
        ("parse 现有 lua", test_parse_lua),
        ("round-trip 序列化", test_round_trip),
        ("备份功能", test_backup),
        ("错误处理", test_parse_error),
    ]

    failed = 0
    for name, test in tests:
        print(f"\n[{name}]")
        try:
            test()
            print(f"  ✓ PASS")
        except AssertionError as exc:
            print(f"  ✗ FAIL: {exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ ERROR: {exc}")
            failed += 1

    print("\n" + "=" * 60)
    if failed:
        print(f"失败 {failed} 项")
        return 1
    print(f"全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
