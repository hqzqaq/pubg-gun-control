"""
闭环弹道校准向导对话框

从编辑器"工具 → 闭环弹道校准…"打开，对当前选中枪械执行闭环迭代校准：
  - 参数区：射击间隔 / 整匣发数 / 每轮梭数 / 最大轮次
  - 执行区：日志输出 + 扫射确认按钮（替代 CLI 的回车确认）
  - 校准在 QThread 中运行，通过信号与 GUI 通信，不阻塞界面
  - 结果应用到编辑器内存配置（不直接写文件），由用户走正常保存流程

@author hqzqaq
@since 2026-08-13
@version 1.0
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..ballistic_data import BallisticConfig
from ..recoil_calibrator import (
    GUN_RPM,
    CalibResult,
    CalibrationAborted,
    RecoilCalibrator,
    rpm_to_interval_ms,
)

logger = logging.getLogger(__name__)


class CalibrationWorker(QObject):
    """校准工作线程封装"""

    logEmitted = Signal(str)
    promptRequested = Signal(str)
    finishedOk = Signal(object)  # CalibResult
    failed = Signal(str)
    aborted = Signal()

    def __init__(
        self,
        calibrator: RecoilCalibrator,
        max_rounds: int,
        prompt_event: threading.Event,
    ) -> None:
        super().__init__()
        self._cal = calibrator
        self._max_rounds = max_rounds
        self._prompt_event = prompt_event

    def prompt(self, msg: str) -> None:
        """在工作线程中被调用：发信号给 GUI，阻塞等待用户点击确认"""
        self.promptRequested.emit(msg)
        self._prompt_event.wait()
        self._prompt_event.clear()

    def run(self) -> None:
        try:
            result = self._cal.run(max_rounds=self._max_rounds)
        except CalibrationAborted:
            self.aborted.emit()
            return
        except Exception as exc:  # noqa: BLE001 - 任何异常都要回到 GUI
            logger.exception("校准线程异常")
            self.failed.emit(str(exc))
            return
        if result is None:
            self.failed.emit("校准未完成（无有效数据或注入被拦截），详见日志。")
        else:
            self.finishedOk.emit(result)


class CalibrationDialog(QDialog):
    """闭环弹道校准向导（非模态，方便切换到游戏窗口）"""

    calibrationApplied = Signal(str)  # 枪名
    # manual 模式：每轮迭代出新表时发出（interval, ballistic），
    # 由主窗口走与"保存到 lua"相同的写回流程（.bak 备份 + dofile 同步），供 GHUB 读取
    roundTableReady = Signal(int, object)

    def __init__(
        self,
        parent: QWidget,
        config: BallisticConfig,
        lua_path: str,
        gun_name: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"闭环弹道校准 - {gun_name}")
        self.resize(640, 560)
        self.setModal(False)

        self._config = config
        self._lua_path = lua_path
        self._gun_name = gun_name
        self._result: CalibResult | None = None
        self._calibrator: RecoilCalibrator | None = None
        self._thread: QThread | None = None
        self._worker: CalibrationWorker | None = None
        self._prompt_event = threading.Event()

        self._build_ui()
        self._load_defaults()

    # ---- UI ----

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "使用步骤：进入训练场，站立 + 红点/全息，准星压在墙面固定参照物上；\n"
            "点击下方【开始校准】，每梭扫射前点【确认，开始监听】；\n"
            "建议用 Alt+Tab 切回游戏（点鼠标切窗会误触射击），然后按住左键打满整匣。\n"
            "不足 0.5 秒的短按压（如切窗点击）会被自动忽略，继续监听。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 参数区
        form = QFormLayout()
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(10, 500)
        self._interval_spin.setSuffix(" ms")
        form.addRow("射击间隔", self._interval_spin)

        self._bullets_spin = QSpinBox()
        self._bullets_spin.setRange(5, 200)
        form.addRow("整匣发数", self._bullets_spin)

        self._mags_spin = QSpinBox()
        self._mags_spin.setRange(1, 5)
        self._mags_spin.setValue(2)
        form.addRow("每轮梭数", self._mags_spin)

        self._rounds_spin = QSpinBox()
        self._rounds_spin.setRange(1, 8)
        self._rounds_spin.setValue(4)
        form.addRow("最大迭代轮次", self._rounds_spin)

        self._manual_check = QCheckBox("GHUB 手动模式（每轮写入 lua，由 GHUB 脚本压枪）")
        self._manual_check.setToolTip(
            "当 SendInput 注入被游戏拦截时使用：校准器不再自己压枪，\n"
            "而是每轮把迭代出的弹道表写回 lua（走编辑器保存流程），\n"
            "你在 GHUB 中重载脚本后扫射，校准器只负责测量残余误差。"
        )
        form.addRow("", self._manual_check)
        layout.addLayout(form)

        # 状态 + 确认
        row = QHBoxLayout()
        self._state_label = QLabel("未开始")
        row.addWidget(self._state_label, 1)
        self._confirm_btn = QPushButton("确认，开始监听")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        row.addWidget(self._confirm_btn)
        layout.addLayout(row)

        # 日志
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        layout.addWidget(self._log_view, 1)

        # 底部按钮
        btns = QDialogButtonBox()
        self._start_btn = QPushButton("开始校准")
        self._start_btn.clicked.connect(self._on_start)
        btns.addButton(self._start_btn, QDialogButtonBox.ActionRole)

        self._abort_btn = QPushButton("中止")
        self._abort_btn.setEnabled(False)
        self._abort_btn.clicked.connect(self._on_abort)
        btns.addButton(self._abort_btn, QDialogButtonBox.ActionRole)

        self._apply_btn = QPushButton("应用结果")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        btns.addButton(self._apply_btn, QDialogButtonBox.AcceptRole)

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.close)
        btns.addButton(self._close_btn, QDialogButtonBox.RejectRole)
        layout.addWidget(btns)

    def _load_defaults(self) -> None:
        rpm = GUN_RPM.get(self._gun_name)
        gun = self._config.find_gun(self._gun_name)
        if rpm:
            self._interval_spin.setValue(rpm_to_interval_ms(rpm))
        elif gun is not None:
            self._interval_spin.setValue(gun.interval)
        bullets = 110 if self._gun_name == "RPD" else 40
        if gun is not None and gun.ballistic:
            bullets = max(bullets, gun.ballistic[-1][0])
        self._bullets_spin.setValue(bullets)

    # ---- 流程 ----

    def _create_worker(self) -> CalibrationWorker:
        """创建校准器 + 工作对象，并把校准器的控制台 IO 替换为 GUI 信号回调

        关键：RecoilCalibrator 默认用 input()/print（CLI 模式），
        在 GUI 线程里 input() 会永远阻塞——必须在这里注入信号回调。
        """
        calibrator = RecoilCalibrator(
            gun=self._gun_name,
            interval_ms=self._interval_spin.value(),
            n_bullets=self._bullets_spin.value(),
            lua_path=Path(self._lua_path),
            mags_per_round=self._mags_spin.value(),
            mode="manual" if self._manual_check.isChecked() else "auto",
            write_fn=self._write_table_gui,
        )
        worker = CalibrationWorker(
            calibrator, self._rounds_spin.value(), self._prompt_event
        )
        calibrator.set_io(
            prompt_fn=worker.prompt,
            log_fn=worker.logEmitted.emit,
        )
        self._calibrator = calibrator
        return worker

    def _write_table_gui(self, gun: str, interval_ms: int, ballistic: list) -> None:
        """manual 模式的写表回调（在工作线程中调用）

        只发信号，由主窗口在 GUI 线程中走编辑器保存流程
        （.bak 备份 + dofile 同步），保证 GHUB 能读到最新弹道。
        """
        self.roundTableReady.emit(interval_ms, ballistic)

    def _on_start(self) -> None:
        try:
            self._worker = self._create_worker()
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"初始化失败: {exc}")
            return
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.logEmitted.connect(self._append_log)
        self._worker.promptRequested.connect(self._on_prompt)
        self._worker.finishedOk.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.aborted.connect(self._on_aborted)
        self._worker.finishedOk.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.aborted.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._start_btn.setEnabled(False)
        self._abort_btn.setEnabled(True)
        self._apply_btn.setEnabled(False)
        self._set_params_enabled(False)
        self._state_label.setText("校准中……")
        self._log_view.clear()
        self._thread.start()

    def _on_prompt(self, msg: str) -> None:
        self._state_label.setText(msg)
        self._confirm_btn.setEnabled(True)

    def _on_confirm(self) -> None:
        self._confirm_btn.setEnabled(False)
        self._state_label.setText("监听中——Alt+Tab 切到游戏，按住左键扫射（短点击会被忽略）")
        self._prompt_event.set()

    def _on_finished(self, result: CalibResult) -> None:
        self._result = result
        lines = ["校准完成，弹道表：", f"  interval = {result.interval_ms},"]
        lines += [f"  {{{n}, {v}}}," for n, v in result.ballistic]
        lines.append(
            f"残余 RMS {result.residual_rms_px:.2f}px | 增益 γ {result.gain:.3f}"
        )
        self._append_log("\n".join(lines))
        self._state_label.setText("完成——点击【应用结果】写入选中枪械")
        self._apply_btn.setEnabled(True)
        self._reset_run_state()

    def _on_failed(self, msg: str) -> None:
        self._append_log(f"校准失败：{msg}")
        self._state_label.setText("失败")
        self._reset_run_state()

    def _on_aborted(self) -> None:
        self._append_log("已中止。")
        self._state_label.setText("已中止")
        self._reset_run_state()

    def _on_abort(self) -> None:
        if self._calibrator is not None:
            self._calibrator.request_abort()
        self._prompt_event.set()  # 防止阻塞在确认等待上
        self._state_label.setText("将在当前扫射结束后中止……")
        self._abort_btn.setEnabled(False)

    def _on_apply(self) -> None:
        if self._result is None:
            return
        gun = self._config.find_gun(self._gun_name)
        if gun is None:
            self._append_log(f"错误：配置中找不到 {self._gun_name}")
            return
        gun.interval = self._result.interval_ms
        gun.ballistic = self._result.ballistic
        self.calibrationApplied.emit(self._gun_name)
        self._append_log(f"已应用到 [{self._gun_name}]（未保存，请用 Ctrl+S 保存）")
        self._apply_btn.setEnabled(False)

    # ---- 辅助 ----

    def _append_log(self, msg: str) -> None:
        self._log_view.appendPlainText(msg)

    def _set_params_enabled(self, enabled: bool) -> None:
        for w in (
            self._interval_spin,
            self._bullets_spin,
            self._mags_spin,
            self._rounds_spin,
            self._manual_check,
        ):
            w.setEnabled(enabled)

    def _reset_run_state(self) -> None:
        self._start_btn.setEnabled(True)
        self._abort_btn.setEnabled(False)
        self._confirm_btn.setEnabled(False)
        self._set_params_enabled(True)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._thread is not None and self._thread.isRunning():
            self._on_abort()
            self._thread.wait(3000)
        event.accept()
