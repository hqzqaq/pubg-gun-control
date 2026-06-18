"""
编辑器集成测试

测试整个编辑器流程：
  1. 解析 lua
  2. 实例化主窗口
  3. 加载配置
  4. 选中枪支
  5. 验证轨迹图渲染
  6. 修改系数 → 验证回写
  7. 保存 → 重新解析 → 验证
  8. 预设保存/加载

@author huquanzhi
@since 2026-06-18 20:00
@version 1.0
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# 无头模式：在没有显示器的环境运行（CI）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from pubg_gun_control.config_manager import (  # noqa: E402
    add_editor_recent,
    clear_editor_recent,
    load_editor_recent,
)
from pubg_gun_control.editor_ui.main_window import BallisticEditorWindow  # noqa: E402
from pubg_gun_control.editor_ui.trajectory_view import TrajectoryCalculator  # noqa: E402
from pubg_gun_control.lua_parser import LuaBallisticParser  # noqa: E402
from pubg_gun_control.preset_manager import PresetError, PresetManager  # noqa: E402


# 抑制所有 QMessageBox 弹窗（测试环境无人工交互）
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
QMessageBox.about = staticmethod(lambda *a, **k: None)


LUA_FILE = PROJECT_ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua"


def test_trajectory_calculator() -> None:
    """测试弹道计算"""
    print("\n[1] 弹道计算器")
    parser = LuaBallisticParser()
    config = parser.parse(LUA_FILE)
    m762 = config.find_gun("Beryl M762")
    assert m762 is not None

    # 满配轨迹
    points = TrajectoryCalculator.calculate(m762, attachment_multiplier=0.7)
    assert len(points) == 30, f"应有 30 发，实际 {len(points)}"
    print(f"  [OK] 生成 30 发轨迹，末发偏移 dx={points[-1].dx:.2f}, dy={points[-1].dy:.2f}")

    # 裸配轨迹
    bare_points = TrajectoryCalculator.calculate(m762, attachment_multiplier=1.0)
    assert bare_points[-1].dy > points[-1].dy, "裸配偏移应大于满配"
    print(f"  [OK] 裸配末发 dy={bare_points[-1].dy:.2f} > 满配 dy={points[-1].dy:.2f}")

    # 禁用模式
    dp28 = config.find_gun("DP-28")
    assert dp28 is not None and dp28.mode == 0
    disabled = TrajectoryCalculator.calculate(dp28)
    assert len(disabled) == 0, "禁用模式应返回空"
    print(f"  [OK] 禁用模式 (DP-28 mode=0) 返回空列表")


def test_editor_window() -> None:
    """测试编辑器主窗口"""
    print("\n[2] 编辑器主窗口")
    app = QApplication.instance() or QApplication(sys.argv)

    # 复制 lua 到临时文件，避免污染原文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lua", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(LUA_FILE.read_text(encoding="utf-8"))
        tmp_path = Path(tmp.name)

    try:
        window = BallisticEditorWindow(lua_path=str(tmp_path))
        window.show()
        app.processEvents()
        assert window._config is not None
        assert window._lua_path == str(tmp_path)
        print(f"  [OK] 窗口创建并加载配置，枪械总数: {sum(len(g) for g in window._config.ammo_groups.values())}")

        # 选中 M762
        window._on_gun_selected("Beryl M762")
        app.processEvents()
        assert window._current_gun_name == "Beryl M762"
        print(f"  [OK] 选中 M762 后状态正确")

        # 修改系数
        m762 = window._config.find_gun("Beryl M762")
        original_coef = m762.coef
        window._detail_panel._spins["coef"].setValue(9.99)
        app.processEvents()
        assert abs(m762.coef - 9.99) < 0.001, f"修改未生效: {m762.coef}"
        assert window._dirty
        print(f"  [OK] 系数修改 {original_coef} -> 9.99，dirty 标志置位")

        # 切换模式
        window._detail_panel._mode_combo.setCurrentIndex(2)  # 连点
        app.processEvents()
        assert m762.mode == 2
        print(f"  [OK] 模式切换为 2 (连点)")

        # 保存
        window._on_save_lua()
        app.processEvents()
        # 重新解析
        parser = LuaBallisticParser()
        config2 = parser.parse(tmp_path)
        m762_2 = config2.find_gun("Beryl M762")
        assert abs(m762_2.coef - 9.99) < 0.001
        assert m762_2.mode == 2
        print(f"  [OK] 保存后重新解析，新值生效")

        window.close()
    finally:
        tmp_path.unlink(missing_ok=True)
        bak = tmp_path.with_suffix(tmp_path.suffix + ".bak")
        bak.unlink(missing_ok=True)


def test_preset_manager() -> None:
    """测试预设管理器"""
    print("\n[3] 预设管理器")
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = PresetManager(tmp_dir)

        parser = LuaBallisticParser()
        config = parser.parse(LUA_FILE)

        # 保存
        target = mgr.save_preset("test_m762_1400", config, description="测试")
        assert target.exists()
        print(f"  [OK] 保存预设 test_m762_1400 -> {target.name}")

        # 重复保存应失败
        try:
            mgr.save_preset("test_m762_1400", config)
            assert False, "应抛异常"
        except PresetError as exc:
            print(f"  [OK] 重复保存被拒绝: {exc}")

        # 加载
        preset = mgr.load_preset("test_m762_1400")
        assert preset.name == "test_m762_1400"
        assert preset.config.find_gun("Beryl M762") is not None
        print(f"  [OK] 加载预设成功，description={preset.description!r}")

        # 列表
        presets = mgr.list_presets()
        assert "test_m762_1400" in presets
        print(f"  [OK] 列表包含预设: {presets}")

        # 不合法名称
        try:
            mgr.save_preset("bad name with space", config)
            assert False, "应抛异常"
        except PresetError as exc:
            print(f"  [OK] 非法名称被拒绝: {exc}")

        # 删除
        mgr.delete_preset("test_m762_1400")
        assert not mgr.preset_exists("test_m762_1400")
        print(f"  [OK] 删除成功")


def test_recent_files() -> None:
    """测试最近文件管理"""
    print("\n[4] 最近文件管理")
    # 清空
    clear_editor_recent()
    assert load_editor_recent() == []
    print(f"  [OK] 清空后列表为空")

    # 添加
    files = [
        str(PROJECT_ROOT / "1.2.2-2024.5.20.-GHUB.-github.lua"),
        str(PROJECT_ROOT / "back.lua"),
    ]
    for f in files:
        add_editor_recent(f)
    loaded = load_editor_recent()
    assert len(loaded) == 2
    print(f"  [OK] 添加 2 个文件，列表长度: {len(loaded)}")

    # 重复添加：去重
    add_editor_recent(files[0])
    loaded = load_editor_recent()
    assert len(loaded) == 2
    assert loaded[0] == str(Path(files[0]).resolve())
    print(f"  [OK] 重复添加去重，最新在前")

    # 清理
    clear_editor_recent()


def main() -> int:
    print("=" * 60)
    print("编辑器集成测试")
    print("=" * 60)

    tests = [
        ("弹道计算器", test_trajectory_calculator),
        ("编辑器主窗口", test_editor_window),
        ("预设管理器", test_preset_manager),
        ("最近文件", test_recent_files),
    ]

    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"  >>> PASS: {name}")
        except AssertionError as exc:
            print(f"  >>> FAIL [{name}]: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  >>> ERROR [{name}]: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed:
        print(f"失败 {failed} 项")
        return 1
    print(f"全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
