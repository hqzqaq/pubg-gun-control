"""
校准对话框与校准器回调注入测试

- RecoilCalibrator 的 prompt_fn/log_fn 回调路由（不依赖屏幕/鼠标）
- request_abort 中止
- CalibrationDialog 冒烟测试（offscreen）：默认值、按钮状态、应用结果回写配置

@author hqzqaq
@since 2026-08-13
@version 1.0
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pubg_gun_control.lua_parser import LuaBallisticParser  # noqa: E402
from pubg_gun_control.recoil_calibrator import (  # noqa: E402
    CalibResult,
    CalibrationAborted,
    RecoilCalibrator,
    SpraySession,
)

LUA_FILE = PROJECT_ROOT / "pubg_config.lua"


# ---------------------------------------------------------------------------
# 回调注入与中止
# ---------------------------------------------------------------------------


class _FakeRecorder:
    """模拟 record_one 直接返回合成轨迹"""

    def __init__(self, n_samples: int = 100) -> None:
        self.calls = 0
        self._n = n_samples

    def record_one(self, compensator=None, max_seconds=60.0, **kw):
        self.calls += 1
        s = SpraySession()
        s.samples = [
            (float(i * 10), 0.0, float(i)) for i in range(self._n)
        ]
        return s


def _make_calibrator(**kw) -> RecoilCalibrator:
    return RecoilCalibrator(
        gun="RPD", interval_ms=80, n_bullets=100, lua_path=LUA_FILE, **kw
    )


def test_prompt_and_log_callbacks_are_used() -> None:
    prompts: list[str] = []
    logs: list[str] = []
    cal = _make_calibrator(
        mags_per_round=2,
        prompt_fn=lambda msg: prompts.append(msg),
        log_fn=lambda msg: logs.append(msg),
    )
    sessions = cal._record_round(_FakeRecorder(), None, "测试轮")
    assert len(sessions) == 2          # 两梭都记录
    assert len(prompts) == 2           # 每梭一次确认
    assert any("测试轮" in m for m in logs)


def test_abort_between_mags() -> None:
    cal = _make_calibrator(mags_per_round=3, prompt_fn=lambda m: None, log_fn=lambda m: None)
    cal.request_abort()
    with pytest.raises(CalibrationAborted):
        cal._record_round(_FakeRecorder(), None, "中止轮")


# ---------------------------------------------------------------------------
# 对话框冒烟测试
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_dialog_defaults_for_rpd(qapp) -> None:
    from pubg_gun_control.editor_ui.calibration_dialog import CalibrationDialog

    config = LuaBallisticParser().parse(LUA_FILE)
    dlg = CalibrationDialog(None, config, str(LUA_FILE), "RPD")
    assert dlg._interval_spin.value() == 80   # RPD 750 RPM
    assert dlg._bullets_spin.value() == 110   # RPD 扩容弹匣
    assert not dlg._confirm_btn.isEnabled()
    assert not dlg._apply_btn.isEnabled()
    assert dlg._start_btn.isEnabled()
    dlg.close()


def test_dialog_apply_writes_memory_config(qapp) -> None:
    from pubg_gun_control.editor_ui.calibration_dialog import CalibrationDialog

    config = LuaBallisticParser().parse(LUA_FILE)
    dlg = CalibrationDialog(None, config, str(LUA_FILE), "RPD")

    applied: list[str] = []
    dlg.calibrationApplied.connect(applied.append)

    new_table = [(1, 0.0), (50, 4.0), (110, 5.0)]
    dlg._result = CalibResult(
        gun="RPD",
        interval_ms=80,
        n_bullets=110,
        per_bullet_px=np.zeros(110),
        ballistic=new_table,
        residual_rms_px=0.8,
        gain=0.6,
    )
    dlg._on_apply()

    rpd = config.find_gun("RPD")
    assert rpd.interval == 80
    assert rpd.ballistic == new_table
    assert applied == ["RPD"]
    dlg.close()


def test_dialog_wires_calibrator_io_to_signals(qapp) -> None:
    """回归：校准器 IO 必须接到 worker 的信号回调上

    曾有的 bug：_on_start 未注入 prompt_fn/log_fn，校准器回退到
    控制台 input()，在工作线程中永久阻塞，界面卡在"校准中……"。
    """
    from pubg_gun_control.editor_ui.calibration_dialog import CalibrationDialog

    config = LuaBallisticParser().parse(LUA_FILE)
    dlg = CalibrationDialog(None, config, str(LUA_FILE), "RPD")
    worker = dlg._create_worker()
    cal = dlg._calibrator

    # 回调已被替换为 worker 的信号实现，而不是默认的 input/print
    assert cal._prompt == worker.prompt
    assert cal._log == worker.logEmitted.emit

    # prompt 调用会发出 promptRequested 信号（事件预置，避免阻塞）
    prompts: list[str] = []
    logs: list[str] = []
    worker.promptRequested.connect(prompts.append)
    worker.logEmitted.connect(logs.append)
    dlg._prompt_event.set()
    cal._prompt("请确认")
    cal._log("测试日志")
    assert prompts == ["请确认"]
    assert logs == ["测试日志"]
    dlg.close()
