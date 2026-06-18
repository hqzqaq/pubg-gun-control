"""
枪械明细面板

8 个 QDoubleSpinBox（自身/下蹲/屏息/裸配/满配/趴姿/2 倍/3 倍系数）
+ 1 个 mode QComboBox。

修改时发出 data_changed 信号，让主窗口联动轨迹图与列表。

@author huquanzhi
@since 2026-06-18 19:50
@version 1.0
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..ballistic_data import GunCoefficients


# (字段名, 中文标签, 步长, 范围, 小数位)
_COEFF_FIELDS = [
    ("coef",    "自身系数",    0.01, (0.0, 20.0), 2),
    ("crouch",  "下蹲系数",    0.01, (0.0, 5.0),  2),
    ("breath",  "屏息系数",    0.01, (0.0, 5.0),  2),
    ("bare",    "裸配系数",    0.01, (0.0, 5.0),  2),
    ("full",    "满配系数",    0.01, (0.0, 10.0), 2),
    ("prone",   "趴姿系数",    0.01, (0.0, 5.0),  2),
    ("scope2x", "2 倍镜系数",  0.01, (0.0, 5.0),  2),
    ("scope3x", "3 倍镜系数",  0.01, (0.0, 5.0),  2),
]
_MODE_OPTIONS = [(0, "0 - 禁用"), (1, "1 - 启用"), (2, "2 - 连点")]


class GunDetailPanel(QWidget):
    """中部枪械明细编辑面板"""

    data_changed = Signal()  # 任何字段变化时发出

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gun: GunCoefficients | None = None
        self._spins: dict[str, QDoubleSpinBox] = {}
        self._mode_combo: QComboBox | None = None
        self._updating = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        self._title = QLabel("未选中")
        self._title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ff9800;"
        )
        layout.addWidget(self._title)

        # 模式选择
        mode_frame = QFrame()
        mode_frame.setFrameShape(QFrame.StyledPanel)
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(8, 4, 8, 4)
        mode_layout.addWidget(QLabel("模式:"))
        self._mode_combo = QComboBox()
        for value, label in _MODE_OPTIONS:
            self._mode_combo.addItem(label, userData=value)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()
        layout.addWidget(mode_frame)

        # 8 个系数 spinbox
        form = QFormLayout()
        form.setSpacing(4)
        for field_name, label_text, step, (lo, hi), decimals in _COEFF_FIELDS:
            spin = QDoubleSpinBox()
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
            spin.setRange(lo, hi)
            spin.setMinimumWidth(120)
            spin.valueChanged.connect(self._on_spin_changed)
            self._spins[field_name] = spin
            form.addRow(f"{label_text}:", spin)
        layout.addLayout(form)
        layout.addStretch()

    def set_gun(self, gun: GunCoefficients | None) -> None:
        """填充数据；None 时清空"""
        self._gun = gun
        self._updating = True
        try:
            if gun is None:
                self._title.setText("未选中")
                for spin in self._spins.values():
                    spin.setValue(0.0)
                    spin.setEnabled(False)
                self._mode_combo.setEnabled(False)
                self._mode_combo.setCurrentIndex(0)
            else:
                self._title.setText(f"{gun.name}")
                for field_name, spin in self._spins.items():
                    spin.setValue(getattr(gun, field_name))
                    spin.setEnabled(True)
                self._mode_combo.setEnabled(True)
                for i in range(self._mode_combo.count()):
                    if self._mode_combo.itemData(i) == gun.mode:
                        self._mode_combo.setCurrentIndex(i)
                        break
        finally:
            self._updating = False

    def apply_to_gun(self) -> None:
        """把面板当前值回写到 self._gun（用户每次修改后自动调用）"""
        if self._gun is None or self._updating:
            return
        for field_name, spin in self._spins.items():
            setattr(self._gun, field_name, spin.value())
        self._gun.mode = self._mode_combo.currentData()

    def _on_spin_changed(self, _value: float) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self.data_changed.emit()

    def _on_mode_changed(self, _index: int) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self.data_changed.emit()
