"""
枪械明细面板

10 个 QDoubleSpinBox（自身/下蹲/屏息/裸配/满配/趴姿/2 倍/3 倍/4 倍/6 倍系数）
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
    QSpinBox,
    QTextEdit,
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
    ("scope4x", "4 倍镜系数",  0.01, (0.0, 5.0),  2),
    ("scope6x", "6 倍镜系数",  0.01, (0.0, 5.0),  2),
]
# 姿态类系数的悬浮说明（这两个是乘数，新手最容易填反）
_COEFF_TOOLTIPS: dict[str, str] = {
    "crouch": "下蹲时的压枪量乘数。1.00 = 该枪蹲下没有后坐减免；"
              "填 0 会让压枪量归零，等同完全不压枪，切勿填 0。\n"
              "注意：基准姿态设为「蹲下」时，站立补偿 = 1 ÷ 本值，"
              "所以本值越小站立压得越狠（想加大站立补偿要调小，不是调大）",
    "prone": "趴下时的压枪量乘数。1.00 = 该枪趴下没有后坐减免；"
             "填 0 会让压枪量归零，等同完全不压枪，切勿填 0",
    "bare": "【已废弃】裸配系数只写进 gunOptions 表，getRealY 从不读取，改它没有任何效果。"
            "配件效果由 attachmentConfig（枪口 × 握把 × 枪托）实时计算",
    "full": "【已废弃】满配系数只写进 gunOptions 表，getRealY 从不读取，改它没有任何效果。"
            "配件效果由 attachmentConfig（枪口 × 握把 × 枪托）实时计算",
}
_DEFAULT_COEFF_TOOLTIP = "乘数：1.00 = 不缩放（无影响）"

# 已废弃的字段，界面上打灰标
_DEPRECATED_FIELDS = ("bare", "full")

_MODE_OPTIONS = [(0, "0 - 禁用"), (1, "1 - 启用"), (2, "2 - 连点")]


class GunDetailPanel(QWidget):
    """中部枪械明细编辑面板"""

    data_changed = Signal()  # 任何字段变化时发出

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gun: GunCoefficients | None = None
        self._spins: dict[str, QDoubleSpinBox] = {}
        self._mode_combo: QComboBox | None = None
        self._interval_spin: QSpinBox | None = None
        self._ballistic_edit: QTextEdit | None = None
        self._updating = False
        self._stance_base = "stand"  # 弹道表基准姿态：stand | crouch
        self._stance_hint: QLabel | None = None
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

        # 10 个系数 spinbox（两列布局，紧凑显示）
        form_left = QFormLayout()
        form_left.setSpacing(4)
        form_right = QFormLayout()
        form_right.setSpacing(4)
        half = (len(_COEFF_FIELDS) + 1) // 2
        for i, (field_name, label_text, step, (lo, hi), decimals) in enumerate(_COEFF_FIELDS):
            if field_name in _DEPRECATED_FIELDS:
                label_text = f"{label_text}(废弃)"
            spin = QDoubleSpinBox()
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
            spin.setRange(lo, hi)
            spin.setMinimumWidth(110)
            spin.valueChanged.connect(self._on_spin_changed)
            spin.setToolTip(
                _COEFF_TOOLTIPS.get(field_name, _DEFAULT_COEFF_TOOLTIP)
            )
            self._spins[field_name] = spin
            if i < half:
                form_left.addRow(f"{label_text}:", spin)
            else:
                form_right.addRow(f"{label_text}:", spin)
        coeff_row = QHBoxLayout()
        coeff_row.addLayout(form_left)
        coeff_row.addLayout(form_right)
        layout.addLayout(coeff_row)

        # 实际生效倍数实时显示（把「1 ÷ 下蹲系数」这种反直觉换算摆到明面上）
        self._stance_hint = QLabel("—")
        self._stance_hint.setWordWrap(True)
        self._stance_hint.setStyleSheet(
            "color: #4fc3f7; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self._stance_hint)

        stance_tip = QLabel(
            "下蹲 / 趴姿系数是乘数：1.00 = 该姿态没有后坐减免，"
            "0.60 = 后坐只有站立的 60%。填 0 会让压枪量归零，切勿填 0。\n"
            "裸配 / 满配系数已废弃（脚本不读取），配件走 attachmentConfig 实时计算。"
        )
        stance_tip.setWordWrap(True)
        stance_tip.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(stance_tip)

        # 射击间隔
        interval_frame = QFrame()
        interval_frame.setFrameShape(QFrame.StyledPanel)
        interval_layout = QHBoxLayout(interval_frame)
        interval_layout.setContentsMargins(8, 4, 8, 4)
        interval_layout.addWidget(QLabel("射击间隔 (ms):"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 1000)
        self._interval_spin.setSingleStep(1)
        self._interval_spin.valueChanged.connect(self._on_interval_changed)
        interval_layout.addWidget(self._interval_spin)
        interval_layout.addStretch()
        layout.addWidget(interval_frame)

        # 弹道数据
        layout.addWidget(QLabel("弹道数据 (每行: 子弹序号, 累计偏移):"))
        self._ballistic_edit = QTextEdit()
        self._ballistic_edit.setMaximumHeight(160)
        self._ballistic_edit.textChanged.connect(self._on_ballistic_changed)
        layout.addWidget(self._ballistic_edit)

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
                self._interval_spin.setEnabled(False)
                self._interval_spin.setValue(87)
                self._ballistic_edit.setEnabled(False)
                self._ballistic_edit.clear()
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
                self._interval_spin.setEnabled(True)
                self._interval_spin.setValue(gun.interval)
                self._ballistic_edit.setEnabled(True)
                self._ballistic_edit.setPlainText(self._format_ballistic(gun.ballistic))
        finally:
            self._updating = False
        self._refresh_stance_hint()

    def set_stance_base(self, base: str) -> None:
        """设置弹道表基准姿态（stand | crouch），影响实际生效倍数的换算显示"""
        self._stance_base = "crouch" if base == "crouch" else "stand"
        self._refresh_stance_hint()

    def _refresh_stance_hint(self) -> None:
        """把 Lua 里那套倒数换算直接算出来显示，避免用户把方向填反"""
        if self._stance_hint is None:
            return
        gun = self._gun
        if gun is None:
            self._stance_hint.setText("—")
            return
        crouch = self._spins["crouch"].value()
        prone = self._spins["prone"].value()
        if crouch <= 0.01:
            crouch = 1.0
        if prone <= 0.01:
            prone = 1.0
        if self._stance_base == "crouch":
            text = (
                f"弹道基准 = 蹲下 → 实际生效：蹲 ×1.00　站 ×{1 / crouch:.2f}　"
                f"趴 ×{prone / crouch:.2f}"
            )
            if abs(crouch - 1.0) < 0.005:
                text += "　⚠ 下蹲系数=1.00 时站立没有任何补偿，必然压不住"
        else:
            text = (
                f"弹道基准 = 站立 → 实际生效：站 ×1.00　蹲 ×{crouch:.2f}　"
                f"趴 ×{prone:.2f}"
            )
        self._stance_hint.setText(text)

    def apply_to_gun(self) -> None:
        """把面板当前值回写到 self._gun（用户每次修改后自动调用）"""
        if self._gun is None or self._updating:
            return
        for field_name, spin in self._spins.items():
            setattr(self._gun, field_name, spin.value())
        self._gun.mode = self._mode_combo.currentData()
        self._gun.interval = self._interval_spin.value()
        self._gun.ballistic = self._parse_ballistic(self._ballistic_edit.toPlainText())

    @staticmethod
    def _format_ballistic(ballistic: list[tuple[int, float]]) -> str:
        return "\n".join(f"{num}, {offset:g}" for num, offset in ballistic)

    @staticmethod
    def _parse_ballistic(text: str) -> list[tuple[int, float]]:
        result: list[tuple[int, float]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                result.append((int(parts[0]), float(parts[1])))
            except ValueError:
                continue
        return result

    def _on_spin_changed(self, _value: float) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self._refresh_stance_hint()
        self.data_changed.emit()

    def _on_mode_changed(self, _index: int) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self.data_changed.emit()

    def _on_interval_changed(self, _value: int) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self.data_changed.emit()

    def _on_ballistic_changed(self) -> None:
        if self._updating:
            return
        self.apply_to_gun()
        self.data_changed.emit()
