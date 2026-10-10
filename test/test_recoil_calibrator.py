"""
闭环弹道校准器单元测试

不依赖屏幕/鼠标硬件，全部用合成轨迹验证：
  - RPM → interval 换算
  - 逐发切分（cumulative_recoil）
  - 增量/平滑
  - 增益估计与 ILC 更新（模拟线性系统闭环收敛）
  - lua 弹道表生成（自适应分段）
  - 校准结果写回 lua（集成 lua_parser）

@author hqzqaq
@since 2026-08-13
@version 1.0
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pubg_gun_control.recoil_calibrator import (  # noqa: E402
    GUN_RPM,
    RecoilCalibrator,
    SprayRecorder,
    SpraySession,
    build_lua_ballistic,
    cumulative_recoil,
    cumulative_to_per_bullet,
    estimate_gain,
    ilc_update,
    residual_rms,
    rpm_to_interval_ms,
    smooth_deltas,
)
from pubg_gun_control.lua_parser import LuaBallisticParser  # noqa: E402


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _make_session(
    per_bullet_dy: np.ndarray,
    interval_ms: float,
    jitter: float = 0.0,
    seed: int = 0,
) -> SpraySession:
    """按逐发增量合成一条扫射轨迹（每 10ms 一个采样点）"""
    rng = np.random.default_rng(seed)
    cum = np.concatenate([[0.0], np.cumsum(per_bullet_dy)])
    n = len(per_bullet_dy)
    t_end = n * interval_ms
    ts = np.arange(5.0, t_end + 25.0, 10.0)
    # 第 1 发在 t≈0 瞬间击发，第 k 发在 (k-1)*interval 击发
    shot_times = np.arange(0, n) * interval_ms
    dys = np.zeros_like(ts)
    for st, c in zip(shot_times, cum[1:]):
        dys[ts >= st] = c
    dys += rng.normal(0, jitter, size=len(ts))
    session = SpraySession()
    session.samples = [(float(t), 0.0, float(d)) for t, d in zip(ts, dys)]
    return session


# ---------------------------------------------------------------------------
# RPM / interval
# ---------------------------------------------------------------------------


def test_rpm_to_interval() -> None:
    assert rpm_to_interval_ms(750) == 80   # RPD
    assert rpm_to_interval_ms(600) == 100  # AKM
    assert rpm_to_interval_ms(990) == 61   # MG3 高射速
    assert GUN_RPM["RPD"] == 750


# ---------------------------------------------------------------------------
# 逐发切分
# ---------------------------------------------------------------------------


def test_cumulative_recoil_recovers_true_curve() -> None:
    interval = 80.0
    true_deltas = np.full(40, 5.0)  # 每发 5px 恒定后坐
    true_deltas[0] = 12.0           # 首发上跳
    sessions = [_make_session(true_deltas, interval, jitter=0.3, seed=s) for s in range(3)]

    cum_y, _ = cumulative_recoil(sessions, interval, 40)
    expected = np.concatenate([[0.0], np.cumsum(true_deltas)])
    assert cum_y.shape == (41,)
    # 中位数允许少量噪声误差
    np.testing.assert_allclose(cum_y, expected, atol=1.0)


def test_cumulative_recoil_empty_sessions() -> None:
    cum_y, cum_x = cumulative_recoil([], 80.0, 10)
    assert np.all(cum_y == 0)
    assert np.all(cum_x == 0)


def test_cumulative_to_per_bullet_clips_negative() -> None:
    cum = np.array([0.0, 5.0, 9.0, 8.0, 14.0])  # 第 3 发负增量（噪声）
    deltas = cumulative_to_per_bullet(cum)
    assert deltas[2] == 0.0
    assert deltas[0] == 5.0


def test_smooth_deltas_keeps_first_shot() -> None:
    deltas = np.array([12.0, 5.0, 5.2, 4.8, 5.1, 30.0, 5.0, 5.0])
    out = smooth_deltas(deltas, window=3, keep_first=2)
    assert out[0] == 12.0 and out[1] == 5.0  # 前两发不动
    assert out[5] < 30.0  # 中间尖峰被平滑


# ---------------------------------------------------------------------------
# 增益估计与 ILC 闭环收敛（模拟线性系统）
# ---------------------------------------------------------------------------


def test_ilc_converges_in_simulation() -> None:
    """模拟：残余 = 原始 - γ·补偿，验证 2~3 轮收敛"""
    n = 100
    true_gain = 0.62  # 屏幕px/鼠标px
    raw = np.cumsum(np.full(n + 1, 5.0))
    raw[0] = 0.0

    applied = raw.copy()  # 初始猜测 gain=1
    gain = 1.0
    for rnd in range(1, 4):
        residual = raw - true_gain * applied
        if rnd == 1:
            gain = estimate_gain(raw, residual, applied)
            assert abs(gain - true_gain) < 0.05
        applied = ilc_update(applied, residual, gain)

    final_residual = raw - true_gain * applied
    assert residual_rms(final_residual) < 1.0


def test_estimate_gain_degenerate_input() -> None:
    zeros = np.zeros(10)
    assert estimate_gain(zeros, zeros, zeros) == 1.0  # 不崩溃，回退 1.0


# ---------------------------------------------------------------------------
# lua 弹道表生成
# ---------------------------------------------------------------------------


def test_build_lua_ballistic_structure() -> None:
    per_bullet = np.concatenate([[15.0], np.full(99, 8.0)])  # 首发大，其余恒定
    table = build_lua_ballistic(per_bullet, unit_divisor=2.24, rel_tol=0.08)
    assert table[0] == (1, 0.0)          # 首段恒为 0
    assert table[-1][0] == 100           # 末段覆盖总发数
    nums = [n for n, _ in table]
    assert nums == sorted(nums)          # 发数递增
    # 恒定段应被合并成少量关键帧
    assert len(table) < 20
    # 中段值 ≈ 8/2.24 ≈ 3.5
    mid_vals = [v for n, v in table if 20 < n < 90]
    assert all(abs(v - 3.5) <= 0.5 for v in mid_vals)


def test_build_lua_ballistic_tracks_ramp() -> None:
    per_bullet = np.linspace(4.0, 12.0, 100)  # 线性上升
    table = build_lua_ballistic(per_bullet, unit_divisor=1.0, rel_tol=0.08)
    assert table[-1][0] == 100
    values = [v for _, v in table[1:]]
    assert values == sorted(values)  # 单调递增保留趋势
    assert len(table) >= 5           # 坡度应被拆成多段


# ---------------------------------------------------------------------------
# 写回 lua（集成 lua_parser）
# ---------------------------------------------------------------------------


def test_write_to_lua_roundtrip() -> None:
    src = PROJECT_ROOT / "pubg_config.lua"
    with tempfile.TemporaryDirectory() as tmp:
        lua_copy = Path(tmp) / "pubg_config.lua"
        shutil.copy2(src, lua_copy)

        cal = RecoilCalibrator(
            gun="RPD", interval_ms=80, n_bullets=100, lua_path=lua_copy
        )
        # 系数 / 射击间隔以文件当前值为准（用户标定后会变），只验证解析与换算一致
        before = LuaBallisticParser().parse(lua_copy)
        expected_coef = before.find_gun("RPD").coef
        mg3_interval_before = before.find_gun("MG3").interval
        assert abs(cal._gun_coef - expected_coef) < 1e-6
        assert abs(cal._ads_ratio - 0.70) < 1e-6
        assert abs(cal.unit_divisor - cal._ads_ratio * expected_coef) < 1e-6

        new_table = [(1, 0.0), (10, 3.5), (50, 4.0), (100, 4.5)]
        from pubg_gun_control.recoil_calibrator import CalibResult

        result = CalibResult(
            gun="RPD",
            interval_ms=80,
            n_bullets=100,
            per_bullet_px=np.zeros(100),
            ballistic=new_table,
            residual_rms_px=0.5,
            gain=0.62,
        )
        cal.write_to_lua(result, backup=True)

        assert (Path(str(lua_copy) + ".bak")).exists()
        reparsed = LuaBallisticParser().parse(lua_copy)
        rpd = reparsed.find_gun("RPD")
        assert rpd is not None
        assert rpd.interval == 80
        assert rpd.ballistic == new_table
        # 其它枪械不受影响
        mg3 = reparsed.find_gun("MG3")
        assert mg3 is not None and mg3.interval == mg3_interval_before


# ---------------------------------------------------------------------------
# 短点击过滤（切窗点击不应被录成扫射）
# ---------------------------------------------------------------------------


def test_record_one_skips_short_press(monkeypatch) -> None:
    """短按压（如点击游戏窗口获取焦点）应被丢弃并继续监听"""
    logs: list[str] = []
    rec = SprayRecorder(tracker=None, log_fn=logs.append)

    class _DummyListener:
        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr(
        SprayRecorder, "_create_listener", staticmethod(lambda cb: _DummyListener())
    )

    short = SpraySession()
    short.samples = [(float(i * 10), 0.0, 0.0) for i in range(10)]   # 90ms 短按压
    long = SpraySession()
    long.samples = [(float(i * 10), 0.0, 0.0) for i in range(300)]   # ~3s 扫射

    calls = iter([short, long])
    monkeypatch.setattr(rec, "_record_single_press", lambda *a, **kw: next(calls))

    result = rec.record_one(max_seconds=10, min_hold_ms=500)
    assert result is long
    assert any("短按压" in m for m in logs)


def test_record_one_timeout_returns_none(monkeypatch) -> None:
    """一直等不到按压时按超时返回 None"""
    rec = SprayRecorder(tracker=None)

    class _DummyListener:
        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr(
        SprayRecorder, "_create_listener", staticmethod(lambda cb: _DummyListener())
    )
    monkeypatch.setattr(rec, "_record_single_press", lambda *a, **kw: None)

    assert rec.record_one(max_seconds=0.2, min_hold_ms=500) is None


# ---------------------------------------------------------------------------
# 端到端：manual 模式（模拟 GHUB 系统）与裸枪幅值检查
# ---------------------------------------------------------------------------


class _DummyTracker:
    """空 tracker：伪造的 recorder 不使用它"""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def calibrate(self) -> None:
        pass

    def sample(self):
        return None


def _session_from_deltas(deltas: np.ndarray, interval_ms: float) -> SpraySession:
    """按逐发增量（可正可负）合成扫射轨迹"""
    cum = np.concatenate([[0.0], np.cumsum(deltas)])
    n = len(deltas)
    ts = np.arange(5.0, n * interval_ms + 25.0, 10.0)
    shot_times = np.arange(0, n) * interval_ms
    dys = np.zeros_like(ts)
    for st, c in zip(shot_times, cum[1:]):
        dys[ts >= st] = c
    s = SpraySession()
    s.samples = [(float(t), 0.0, float(d)) for t, d in zip(ts, dys)]
    return s


def _expand_table(table: list[tuple[int, float]], n: int) -> np.ndarray:
    """把 [(bullet_end, value), ...] 关键帧展开为逐发数组（索引 0 = 第 1 发）"""
    per = np.zeros(n)
    prev = 0
    for end, val in table:
        end = min(end, n)
        per[prev:end] = val
        prev = end
    return per


class _SimGhubRecorder:
    """模拟"GHUB 按当前 lua 表压枪"的游戏系统

    每次 record_one 返回：原始后坐力 - 当前写入表 × 真实单位效果 的残余轨迹。
    """

    def __init__(self, raw_deltas, unit_effect, interval_ms, state):
        self._raw = raw_deltas
        self._c = unit_effect
        self._interval = interval_ms
        self._state = state

    def record_one(self, compensator=None, max_seconds=60.0, **kw):
        table = self._state.get("table")
        per = (
            _expand_table(table, len(self._raw))
            if table
            else np.zeros(len(self._raw))
        )
        residual = self._raw - self._c * per
        return _session_from_deltas(residual, self._interval)


class _FakeRecorderCal(RecoilCalibrator):
    """注入伪造 recorder 的校准器（不碰屏幕/鼠标）"""

    def __init__(self, *args, fake_recorder=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._fake = fake_recorder

    def _make_recorder(self, tracker):
        return self._fake


def test_manual_mode_converges_with_simulated_ghub() -> None:
    n = 110
    raw = np.full(n, 8.0)
    raw[0] = 0.0    # 第 1 发无补偿
    raw[1] = 15.0   # 首发上跳
    unit_effect = 2.0  # 每个 lua 单位在屏幕上的真实效果（与理论除数不同，考验增益估计）

    state: dict = {}
    writes: list[list] = []

    def write_fn(gun, interval_ms, ballistic):
        state["table"] = ballistic
        writes.append(ballistic)

    fake = _SimGhubRecorder(raw, unit_effect, 80.0, state)
    cal = _FakeRecorderCal(
        gun="RPD",
        interval_ms=80,
        n_bullets=n,
        lua_path=PROJECT_ROOT / "pubg_config.lua",
        mags_per_round=1,
        mode="manual",
        write_fn=write_fn,
        tracker_cls=_DummyTracker,
        prompt_fn=lambda m: None,
        log_fn=lambda m: None,
        fake_recorder=fake,
    )
    result = cal.run(max_rounds=4)

    assert result is not None
    assert len(writes) >= 2  # 至少第 1 轮 + 最终版
    # 最终表 × 真实单位效果 ≈ 原始后坐力
    final_effect = _expand_table(result.ballistic, n) * unit_effect
    err = final_effect[2:] - raw[2:]
    assert float(np.sqrt(np.mean(err**2))) < 2.5


def test_run_aborts_when_raw_recoil_too_small() -> None:
    """裸枪垂直后坐力接近 0（手压/跟丢）→ 直接诊断中止，不误报注入被拦截"""
    raw = np.full(110, 0.05)  # 全程几乎无后坐
    logs: list[str] = []
    fake = _SimGhubRecorder(raw, 1.0, 80.0, {})
    cal = _FakeRecorderCal(
        gun="RPD",
        interval_ms=80,
        n_bullets=110,
        lua_path=PROJECT_ROOT / "pubg_config.lua",
        mags_per_round=1,
        mode="auto",
        tracker_cls=_DummyTracker,
        prompt_fn=lambda m: None,
        log_fn=logs.append,
        fake_recorder=fake,
    )
    assert cal.run(max_rounds=2) is None
    assert any("过低" in m for m in logs)
