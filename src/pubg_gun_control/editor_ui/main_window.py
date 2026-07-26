"""
编辑器主窗口

三栏布局：左侧枪械列表 / 中部明细 / 右侧弹道图
菜单栏：文件 / 预设 / 帮助

@author huquanzhi
@since 2026-06-18 19:55
@version 1.0
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QWidget,
)

from ..ballistic_data import BallisticConfig, BallisticPreset
from ..lua_parser import BallisticParseError, LuaBallisticParser
from ..preset_manager import PresetError, PresetManager
from .attachment_panel import AttachmentPanel
from .gun_detail_panel import GunDetailPanel
from .gun_list_panel import GunListPanel
from .preset_dialog import PresetNameDialog
from .trajectory_view import TrajectoryView


logger = logging.getLogger(__name__)


def _resolve_project_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent


# 默认预设目录
_DEFAULT_PRESETS_DIR = _resolve_project_root() / "presets"


class BallisticEditorWindow(QMainWindow):
    """弹道系数可视化编辑器主窗口"""

    def __init__(self, lua_path: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("弹道系数可视化编辑器")
        self.resize(1280, 800)

        self._lua_path: str = ""
        self._config: BallisticConfig | None = None
        self._parser = LuaBallisticParser()
        self._preset_manager = PresetManager(_DEFAULT_PRESETS_DIR)
        self._current_gun_name: str = ""
        self._dirty = False
        self._recent_files: list[str] = []

        self._build_ui()
        self._build_menus()

        if lua_path:
            self._load_lua_file(lua_path)
        else:
            self._update_status("提示：通过 文件 → 打开 选择 lua 文件")

    # ---- UI ----

    def _build_ui(self) -> None:
        # 中心 splitter
        splitter = QSplitter(Qt.Horizontal)

        self._list_panel = GunListPanel()
        self._detail_panel = GunDetailPanel()
        self._attach_panel = AttachmentPanel()
        self._trajectory_view = TrajectoryView()

        # 右侧放配件 + 轨迹（上下分）
        right = QSplitter(Qt.Vertical)
        right.addWidget(self._attach_panel)
        right.addWidget(self._trajectory_view)
        right.setStretchFactor(0, 1)
        right.setStretchFactor(1, 3)

        splitter.addWidget(self._list_panel)
        splitter.addWidget(self._detail_panel)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([260, 380, 640])

        self.setCentralWidget(splitter)

        # 状态栏
        self.setStatusBar(QStatusBar())
        self._status_label = QLabel("")
        self.statusBar().addPermanentWidget(self._status_label)

        # 信号
        self._list_panel.gun_selected.connect(self._on_gun_selected)
        self._detail_panel.data_changed.connect(self._on_data_changed)
        self._attach_panel.attachments_changed.connect(self._on_attachment_changed)

    def _build_menus(self) -> None:
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        act_open = QAction("打开(&O)…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._on_open)
        file_menu.addAction(act_open)

        self._recent_menu = QMenu("最近打开(&R)", self)
        self._recent_menu.aboutToShow.connect(self._refresh_recent_menu)
        file_menu.addMenu(self._recent_menu)

        file_menu.addSeparator()
        act_save = QAction("保存到 lua(&S)", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._on_save_lua)
        file_menu.addAction(act_save)

        act_save_as = QAction("另存为(&A)…", self)
        act_save_as.triggered.connect(self._on_save_lua_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()
        act_exit = QAction("退出(&X)", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        act_import_ballistic = QAction("导入弹道分析结果…", self)
        act_import_ballistic.triggered.connect(self._on_import_ballistic)
        tools_menu.addAction(act_import_ballistic)

        # 预设菜单
        preset_menu = menubar.addMenu("预设(&P)")

        act_save_preset = QAction("保存当前为预设…", self)
        act_save_preset.triggered.connect(self._on_save_preset)
        preset_menu.addAction(act_save_preset)

        act_load_preset = QAction("加载预设…", self)
        act_load_preset.triggered.connect(self._on_load_preset)
        preset_menu.addAction(act_load_preset)

        act_delete_preset = QAction("删除预设…", self)
        act_delete_preset.triggered.connect(self._on_delete_preset)
        preset_menu.addAction(act_delete_preset)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        act_about = QAction("关于(&A)", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ---- 文件操作 ----

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 GHUB lua 脚本",
            "",
            "Lua 脚本 (*.lua);;所有文件 (*)",
        )
        if path:
            self._load_lua_file(path)

    def _load_lua_file(self, path: str) -> None:
        try:
            config = self._parser.parse(path)
        except BallisticParseError as exc:
            QMessageBox.critical(
                self, "打开失败", f"解析 lua 失败：\n{exc}"
            )
            return

        self._config = config
        self._lua_path = path
        self._list_panel.load_config(config)
        self._attach_panel.set_config(config)
        self._detail_panel.set_gun(None)
        self._trajectory_view.update_view(None)
        self._current_gun_name = ""
        self._dirty = False
        self._update_status(f"已加载: {path}")
        self._add_recent_file(path)

    def _on_save_lua(self) -> None:
        if self._config is None or not self._lua_path:
            QMessageBox.warning(self, "提示", "请先打开一个 lua 文件")
            return
        try:
            self._parser.serialize(self._config, self._lua_path, backup=True)
        except BallisticParseError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self._dirty = False
        bak_path = Path(self._lua_path + ".bak")

        messages: list[str] = [f"已写入：\n{self._lua_path}", f"\n备份文件：\n{bak_path}"]

        # 同步到识别配置中指定的基础脚本（导出 GHUB/dofile 脚本的源文件）
        # 若当前打开的文件即基础脚本，则跳过避免重复写入
        base_sync_msg = self._sync_to_base_lua()
        if base_sync_msg:
            messages.append(base_sync_msg)

        # 同步到 dofile 配置文件
        config_path = _resolve_project_root() / "pubg_config.lua"
        try:
            # 如果 pubg_config.lua 不存在或被污染（含 OnEvent 等执行逻辑），先重新生成纯数据版本
            # 否则 serialize 只替换三段数据块，会保留多余的函数定义和初始化代码
            need_regen = False
            if not config_path.exists():
                need_regen = True
            else:
                existing = config_path.read_text(encoding="utf-8")
                if "function OnEvent" in existing or "\npubg.init()" in existing:
                    need_regen = True
            if need_regen:
                from pubg_gun_control.lua_generator import generate_config_only
                generate_config_only(self._lua_path, config_output=str(config_path))
            self._parser.serialize(self._config, str(config_path), backup=False)
            messages.append(f"\n\ndofile配置已同步: {config_path}")
        except Exception as exc:
            messages.append(f"\n\ndofile配置同步失败: {exc}")

        QMessageBox.information(self, "保存成功", "\n".join(messages))
        self._update_status(f"已保存: {self._lua_path}")

    def _sync_to_base_lua(self) -> str:
        """同步当前配置到识别配置中指定的基础脚本。

        Returns:
            同步结果消息（成功/失败/跳过），空字符串表示无需同步。
        """
        from ..config_manager import load_base_lua_path, load_recognition

        try:
            recognition = load_recognition()
            base_lua_path = load_base_lua_path(recognition)
        except Exception as exc:
            return f"\n\n基础脚本同步失败（读取配置异常）: {exc}"

        if not base_lua_path:
            return ""
        # 当前打开的文件即基础脚本，无需重复写入
        if Path(base_lua_path).resolve() == Path(self._lua_path).resolve():
            return ""
        if not Path(base_lua_path).exists():
            return f"\n\n基础脚本同步失败（文件不存在）: {base_lua_path}"
        try:
            self._parser.serialize(self._config, base_lua_path, backup=True)
            return f"\n\n基础脚本已同步: {base_lua_path}"
        except BallisticParseError as exc:
            return f"\n\n基础脚本同步失败: {exc}"

    def _on_save_lua_as(self) -> None:
        if self._config is None:
            QMessageBox.warning(self, "提示", "请先打开一个 lua 文件")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "Lua 脚本 (*.lua);;所有文件 (*)"
        )
        if not path:
            return
        try:
            self._parser.serialize(self._config, path, backup=False)
        except BallisticParseError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self._lua_path = path
        self._update_status(f"已另存为: {path}")

    def _on_import_ballistic(self) -> None:
        """导入弹道分析生成的 lua 函数，应用到当前或同名枪械"""
        if self._config is None:
            QMessageBox.warning(self, "提示", "请先打开一个 lua 文件")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择弹道分析结果",
            "",
            "Lua 脚本 (*.lua);;所有文件 (*)",
        )
        if not path:
            return

        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "读取失败", f"无法读取文件:\n{exc}")
            return

        funcs = self._parser.parse_gun_functions(content)
        if not funcs:
            QMessageBox.warning(self, "未识别", "未在文件中检测到 pubg[\"GunName\"] 弹道函数")
            return

        # 若只有一个函数直接用它，否则让用户选择
        if len(funcs) == 1:
            src_name = next(iter(funcs))
        else:
            src_name, ok = QInputDialog.getItem(
                self,
                "选择要导入的枪械",
                "文件中包含多把枪械，请选择：",
                list(funcs.keys()),
                0,
                False,
            )
            if not ok or not src_name:
                return

        data = funcs[src_name]
        interval = data["interval"]
        ballistic = data["ballistic"]

        # 决定目标枪械：同名优先，否则当前选中，否则让用户选
        target_name: str | None = None
        if self._config.find_gun(src_name) is not None:
            target_name = src_name
        elif self._current_gun_name and self._config.find_gun(self._current_gun_name) is not None:
            reply = QMessageBox.question(
                self,
                "应用到当前枪械",
                f"文件中为 [{src_name}]，是否将其 interval/ballistic 应用到当前选中的 [{self._current_gun_name}]？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                target_name = self._current_gun_name

        if target_name is None:
            all_guns = [
                g.name for ammo in self._config.ammo_groups.values() for g in ammo
            ]
            target_name, ok = QInputDialog.getItem(
                self,
                "选择目标枪械",
                f"[{src_name}] 与现有枪械名不匹配，请选择要应用的目标枪械：",
                all_guns,
                0,
                False,
            )
            if not ok or not target_name:
                return

        gun = self._config.find_gun(target_name)
        if gun is None:
            QMessageBox.warning(self, "未找到", f"目标枪械 [{target_name}] 不存在")
            return

        gun.interval = interval
        gun.ballistic = ballistic
        self._dirty = True
        self._on_gun_selected(target_name)
        self._update_status(f"已从 [{src_name}] 导入弹道到 [{target_name}]")

    # ---- 枪械联动 ----

    def _on_gun_selected(self, gun_name: str) -> None:
        if self._config is None:
            return
        gun = self._config.find_gun(gun_name)
        if gun is None:
            return
        self._current_gun_name = gun_name
        self._detail_panel.set_gun(gun)
        self._attach_panel.set_gun(gun)
        self._refresh_trajectory()

    def _on_data_changed(self) -> None:
        """明细面板修改了系数"""
        if not self._current_gun_name:
            return
        # 列表的 mode 颜色更新
        gun = self._config.find_gun(self._current_gun_name) if self._config else None
        if gun is not None:
            self._list_panel.update_gun_mode(gun.name, gun.mode)
        self._dirty = True
        self._refresh_trajectory()
        self._update_status("未保存")

    def _on_attachment_changed(self, _category: str, _item_name: str) -> None:
        self._dirty = True
        self._refresh_trajectory()
        self._update_status("未保存")

    def _refresh_trajectory(self) -> None:
        if self._config is None or not self._current_gun_name:
            self._trajectory_view.update_view(None)
            return
        gun = self._config.find_gun(self._current_gun_name)
        if gun is None:
            self._trajectory_view.update_view(None)
            return
        sel = self._attach_panel.get_selected()
        self._trajectory_view.update_view(
            gun,
            muzzle=sel["muzzle"],
            grip=sel["grip"],
            stock=sel["stock"],
        )

    # ---- 预设操作 ----

    def _on_save_preset(self) -> None:
        if self._config is None:
            QMessageBox.warning(self, "提示", "请先打开 lua 文件")
            return
        dlg = PresetNameDialog(self)
        if dlg.exec() != dlg.Accepted:
            return
        try:
            target = self._preset_manager.save_preset(
                dlg.name, self._config, description=dlg.description
            )
        except PresetError as exc:
            QMessageBox.critical(self, "保存预设失败", str(exc))
            return
        QMessageBox.information(self, "已保存", f"预设文件：\n{target}")
        self._update_status(f"已保存预设: {dlg.name}")

    def _on_load_preset(self) -> None:
        presets = self._preset_manager.list_presets()
        if not presets:
            QMessageBox.information(self, "提示", "尚无预设，请先保存一个")
            return
        name, ok = QInputDialog.getItem(
            self, "加载预设", "选择预设:", presets, 0, False
        )
        if not ok or not name:
            return
        try:
            preset = self._preset_manager.load_preset(name)
        except PresetError as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
            return
        self._apply_preset(preset)
        self._update_status(f"已加载预设: {name}")

    def _on_delete_preset(self) -> None:
        presets = self._preset_manager.list_presets()
        if not presets:
            QMessageBox.information(self, "提示", "尚无预设")
            return
        name, ok = QInputDialog.getItem(
            self, "删除预设", "选择要删除的预设:", presets, 0, False
        )
        if not ok or not name:
            return
        confirm = QMessageBox.question(
            self, "确认删除", f"确定要删除预设 {name!r} 吗？"
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._preset_manager.delete_preset(name)
        except PresetError as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        self._update_status(f"已删除预设: {name}")

    def _apply_preset(self, preset: BallisticPreset) -> None:
        """把预设的配置应用到当前界面"""
        # 复制：避免修改预设数据
        self._config = BallisticConfig.from_dict(preset.config.to_dict())
        self._list_panel.load_config(self._config)
        self._attach_panel.set_config(self._config)
        if self._current_gun_name:
            self._on_gun_selected(self._current_gun_name)
        else:
            self._detail_panel.set_gun(None)
            self._trajectory_view.update_view(None)

    # ---- 最近文件 ----

    def set_recent_files(self, files: list[str]) -> None:
        self._recent_files = list(files)[:5]

    def get_recent_files(self) -> list[str]:
        return list(self._recent_files)

    def _add_recent_file(self, path: str) -> None:
        path = str(Path(path).resolve())
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:5]

    def _refresh_recent_menu(self) -> None:
        self._recent_menu.clear()
        if not self._recent_files:
            empty = QAction("（无）", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return
        for path in self._recent_files:
            act = QAction(path, self)
            act.triggered.connect(lambda _checked=False, p=path: self._load_lua_file(p))
            self._recent_menu.addAction(act)

    # ---- 其他 ----

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "关于",
            "弹道系数可视化编辑器\n\n"
            "PUBG GHUB 压枪宏配套工具\n"
            "作者: huquanzhi\n"
            "版本: 1.0",
        )

    def _update_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._dirty:
            ret = QMessageBox.question(
                self,
                "未保存的修改",
                "有未保存的修改，确定要退出吗？",
                QMessageBox.Discard | QMessageBox.Save | QMessageBox.Cancel,
            )
            if ret == QMessageBox.Cancel:
                event.ignore()
                return
            if ret == QMessageBox.Save:
                self._on_save_lua()
        event.accept()
