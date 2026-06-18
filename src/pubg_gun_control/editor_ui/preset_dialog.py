"""
预设名称输入对话框

@author huquanzhi
@since 2026-06-18 19:50
@version 1.0
"""

from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class PresetNameDialog(QDialog):
    """输入预设名 + 备注"""

    VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,50}$")

    def __init__(self, parent=None, title: str = "保存预设") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例如 M762_1400dpi_1080p")
        form.addRow("预设名:", self._name_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("备注（DPI、分辨率、鼠标型号等）")
        self._desc_edit.setMaximumHeight(80)
        form.addRow("备注:", self._desc_edit)

        layout.addLayout(form)

        self._hint = QLabel("仅允许字母、数字、下划线、连字符（1~50 字符）")
        self._hint.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self._hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not self.VALID_NAME_RE.match(name):
            self._hint.setText("❌ 名称不合法，请使用 [A-Za-z0-9_-]")
            self._hint.setStyleSheet("color: #f44336; font-size: 10px;")
            return
        self.accept()

    @property
    def name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def description(self) -> str:
        return self._desc_edit.toPlainText().strip()
