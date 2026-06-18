"""
枪械列表面板

按弹药类型分组的 TreeView，模式 0/1/2 用不同图标与颜色。

@author huquanzhi
@since 2026-06-18 19:50
@version 1.0
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from ..ballistic_data import BallisticConfig, GunCoefficients


# mode 颜色：0=禁用/灰、1=启用/绿、2=连点/蓝
_MODE_COLORS = {
    0: QColor("#888"),
    1: QColor("#4caf50"),
    2: QColor("#2196f3"),
}
_MODE_LABELS = {0: "禁用", 1: "启用", 2: "连点"}


class GunListPanel(QWidget):
    """左侧枪械列表面板"""

    gun_selected = Signal(str)  # 发出选中的枪名

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gun_index: dict[str, tuple[str, int]] = {}  # name -> (ammo, idx)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeView()
        self._tree.setHeaderHidden(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setAnimated(True)
        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["枪械 / 弹药", "模式"])
        self._tree.setModel(self._model)
        self._tree.setColumnWidth(0, 160)
        self._tree.setColumnWidth(1, 50)

        self._tree.selectionModel().currentChanged.connect(self._on_selection_changed)

        layout.addWidget(self._tree)

    def load_config(self, config: BallisticConfig) -> None:
        """加载配置并刷新列表"""
        self._model.removeRows(0, self._model.rowCount())
        self._gun_index.clear()

        for ammo, guns in config.ammo_groups.items():
            ammo_item = QStandardItem(f"🔫 {ammo} ({len(guns)})")
            ammo_item.setEditable(False)
            ammo_item.setForeground(QBrush(QColor("#ff9800")))
            ammo_item.setData(None, Qt.UserRole)
            mode_col = QStandardItem("")
            mode_col.setEditable(False)
            self._model.appendRow([ammo_item, mode_col])

            for idx, gun in enumerate(guns):
                name_item = QStandardItem(f"  {gun.name}")
                name_item.setEditable(False)
                name_item.setForeground(QBrush(_MODE_COLORS.get(gun.mode, QColor("#fff"))))
                name_item.setData(gun.name, Qt.UserRole)

                mode_item = QStandardItem(_MODE_LABELS.get(gun.mode, "?"))
                mode_item.setEditable(False)
                mode_item.setForeground(QBrush(_MODE_COLORS.get(gun.mode, QColor("#fff"))))
                mode_item.setTextAlignment(Qt.AlignCenter)

                ammo_item.appendRow([name_item, mode_item])
                self._gun_index[gun.name] = (ammo, idx)

        self._tree.expandAll()

    def update_gun_mode(self, gun_name: str, mode: int) -> None:
        """更新列表中某把枪的 mode 显示"""
        if gun_name not in self._gun_index:
            return
        ammo, _ = self._gun_index[gun_name]
        # 找到对应 item
        for ammo_row in range(self._model.rowCount()):
            ammo_item = self._model.item(ammo_row)
            for gun_row in range(ammo_item.rowCount()):
                gun_item = ammo_item.child(gun_row)
                if gun_item.data(Qt.UserRole) == gun_name:
                    color = _MODE_COLORS.get(mode, QColor("#fff"))
                    gun_item.setForeground(QBrush(color))
                    mode_item = ammo_item.child(gun_row, 1)
                    mode_item.setText(_MODE_LABELS.get(mode, "?"))
                    mode_item.setForeground(QBrush(color))
                    return

    def select_gun(self, gun_name: str) -> None:
        """根据枪名选中列表项"""
        if gun_name not in self._gun_index:
            return
        ammo, _ = self._gun_index[gun_name]
        for ammo_row in range(self._model.rowCount()):
            ammo_item = self._model.item(ammo_row)
            if ammo_item.text().startswith(f"🔫 {ammo}"):
                for gun_row in range(ammo_item.rowCount()):
                    gun_item = ammo_item.child(gun_row)
                    if gun_item.data(Qt.UserRole) == gun_name:
                        index = self._model.indexFromItem(gun_item)
                        self._tree.setCurrentIndex(index)
                        return

    def _on_selection_changed(self, current, _previous) -> None:
        gun_name = current.data(Qt.UserRole)
        if gun_name:
            self.gun_selected.emit(gun_name)
