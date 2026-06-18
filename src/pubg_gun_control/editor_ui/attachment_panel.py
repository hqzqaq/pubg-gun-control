"""
配件选择面板

3 个 Combobox（枪口/握把/枪托），根据 gunNoStock 灰显不可用项。
顶部显示「满配综合系数」实时计算结果。

@author huquanzhi
@since 2026-06-18 19:50
@version 1.0
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..ballistic_data import (
    AttachmentCategory,
    AttachmentItem,
    BallisticConfig,
    GunCoefficients,
)


_CAT_LABELS = {
    "muzzle": "枪口",
    "grip": "握把",
    "stock": "枪托",
}


class AttachmentPanel(QWidget):
    """配件选择面板"""

    attachments_changed = Signal(str, str)  # (category, item_name)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config: BallisticConfig | None = None
        self._gun: GunCoefficients | None = None
        self._combos: dict[str, QComboBox] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("配件组合")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # 综合系数显示
        coef_frame = QFrame()
        coef_frame.setFrameShape(QFrame.StyledPanel)
        coef_frame.setStyleSheet(
            "background: #2d2d30; border-radius: 4px; padding: 6px;"
        )
        coef_layout = QHBoxLayout(coef_frame)
        coef_layout.setContentsMargins(8, 4, 8, 4)
        coef_layout.addWidget(QLabel("满配综合系数:"))
        self._coef_label = QLabel("--")
        self._coef_label.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 14px;")
        coef_layout.addWidget(self._coef_label)
        coef_layout.addStretch()
        layout.addWidget(coef_frame)

        # 三个配件下拉框
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        form.setSpacing(6)
        for cat in ("muzzle", "grip", "stock"):
            combo = QComboBox()
            combo.currentIndexChanged.connect(
                lambda _idx, c=cat: self._on_combo_changed(c)
            )
            self._combos[cat] = combo
            form.addRow(f"{_CAT_LABELS[cat]}:", combo)
        layout.addLayout(form)
        layout.addStretch()

    def set_config(self, config: BallisticConfig) -> None:
        """初始化下拉框内容（在加载 lua 后调用一次）"""
        self._config = config
        has_any = any(
            config.attachment_config.get(cat) is not None
            and config.attachment_config[cat].items
            for cat in ("muzzle", "grip", "stock")
        )
        for cat, combo in self._combos.items():
            combo.blockSignals(True)
            combo.clear()
            category = config.attachment_config.get(cat)
            if category is None or not category.items:
                combo.addItem("（当前 lua 无此段）", userData=None)
                combo.setEnabled(False)
                continue
            for item in category.items:
                combo.addItem(f"{item.label} ({item.ratio:.2f})", userData=item)
            combo.setEnabled(True)
            combo.blockSignals(False)

        if not has_any:
            self._coef_label.setText("--")
            self._coef_label.setToolTip(
                "当前 lua 文件没有 attachmentConfig 段，无法配置配件。"
                "如需编辑配件，请使用 1.2.2-2024.5.20.-GHUB.-github.lua。"
            )
        else:
            self._coef_label.setToolTip("")

    def set_gun(self, gun: GunCoefficients | None) -> None:
        """切换枪支时：灰显 gunNoStock 中的配件槽位"""
        self._gun = gun
        if gun is None or self._config is None:
            for combo in self._combos.values():
                combo.setCurrentIndex(0)
            self._update_coef()
            return

        no_stock = self._config.gun_no_stock.get(gun.name, False)
        for cat, combo in self._combos.items():
            combo.blockSignals(True)
            if cat == "stock" and no_stock:
                combo.setEnabled(False)
                # 强制选 none 项
                for i in range(combo.count()):
                    item = combo.itemData(i)
                    if item is not None and item.name == "none":
                        combo.setCurrentIndex(i)
                        break
            else:
                combo.setEnabled(True)
            combo.blockSignals(False)
        self._update_coef()

    def get_selected(self) -> dict[str, AttachmentItem | None]:
        """返回当前选中的配件（None 表示未选）"""
        result: dict[str, AttachmentItem | None] = {}
        for cat, combo in self._combos.items():
            data = combo.currentData()
            if isinstance(data, AttachmentItem):
                result[cat] = data
            else:
                result[cat] = None
        return result

    def set_selected(self, selections: dict[str, str]) -> None:
        """按 name 设置选中项（用于加载预设）"""
        for cat, name in selections.items():
            combo = self._combos.get(cat)
            if combo is None:
                continue
            for i in range(combo.count()):
                item = combo.itemData(i)
                if isinstance(item, AttachmentItem) and item.name == name:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(i)
                    combo.blockSignals(False)
                    break
        self._update_coef()

    def _on_combo_changed(self, category: str) -> None:
        combo = self._combos[category]
        data = combo.currentData()
        name = data.name if isinstance(data, AttachmentItem) else ""
        self.attachments_changed.emit(category, name)
        self._update_coef()

    def _update_coef(self) -> None:
        if self._gun is None:
            self._coef_label.setText("--")
            return
        sel = self.get_selected()
        m = sel["muzzle"].ratio if sel["muzzle"] else 1.0
        g = sel["grip"].ratio if sel["grip"] else 1.0
        s = sel["stock"].ratio if sel["stock"] else 1.0
        combined = self._gun.coef * m * g * s
        self._coef_label.setText(f"{combined:.2f}")
