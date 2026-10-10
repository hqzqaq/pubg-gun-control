"""
闭环弹道自动校准器

原理：
  扫射时鼠标本身不会移动，后坐力体现为游戏画面（世界参照物）相对屏幕中心的漂移。
  本模块用 mss 高频截取屏幕中心 ROI + cv2 模板匹配，逐帧追踪参照物漂移，
  得到屏幕像素域的后坐力曲线；再按已知射速间隔切成逐发增量。

闭环迭代（ILC）：
  第 0 轮：无补偿裸扫，测原始后坐力曲线 R(k)；
  第 m 轮：SendInput 补偿器按当前补偿表 P(k) 实时压枪，测残余漂移 E(k)，
           由 (R - E) / P 估计屏幕像素↔鼠标像素增益 γ，把 E/γ 加回 P；
  2~3 轮后残余收敛到阈值以内，得到原始鼠标像素域的最终补偿表。

写回 Lua：
  lua 表单位 → 鼠标像素的换算为 V * (ADS/100) * 枪械自身系数（站立/红点基准），
  因此 V(k) = P*(k) / ((ADS/100) * gunCoeff)。倍镜/姿势差异由 lua 侧的
  getRealY 系数处理，校准时请保持站立 + 红点/全息。

用法（CLI 向导）：
  python -m pubg_gun_control.recoil_calibrator --gun RPD

@author hqzqaq
@since 2026-08-13
@version 1.0
"""

from __future__ import annotations

import argparse
import ctypes
import logging
import math
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mss
import numpy as np
from pynput import mouse

from .lua_parser import LuaBallisticParser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 枪械射速表（RPM → 间隔毫秒）
# ---------------------------------------------------------------------------

GUN_RPM: dict[str, int] = {
    "RPD": 750,        # 42.3 新枪，750 RPM ≈ 80ms
    "MG3": 990,        # 高射速模式 ≈ 61ms（660 RPM 模式 ≈ 91ms）
    "M249": 800,
    "M416": 800,
    "AUG": 700,
    "Beryl M762": 700,
    "AKM": 600,
    "Groza": 700,
    "ACE32": 650,
    "SCAR-L": 620,
    "QBZ": 650,
    "G36C": 650,
    "P90": 900,
    "UMP45": 650,
    "Vector": 1090,
    "MP5K": 900,
    "Micro UZI": 1250,
    "Tommy Gun": 725,
    "Famas": 900,
}


def rpm_to_interval_ms(rpm: int) -> int:
    """RPM 换算为射击间隔（毫秒），四舍五入"""
    return int(round(60000.0 / rpm))


# ---------------------------------------------------------------------------
# 屏幕追踪器
# ---------------------------------------------------------------------------


class ScreenTracker:
    """追踪屏幕中心参照物的漂移量

    dy > 0 表示参照物在屏幕上向下移动（准星上跳），即需要向下压枪的量。
    """

    def __init__(
        self,
        roi_w: int = 480,
        roi_h: int = 360,
        template_size: int = 72,
        min_confidence: float = 0.45,
    ) -> None:
        self.roi_w = roi_w
        self.roi_h = roi_h
        self.template_size = template_size
        self.min_confidence = min_confidence
        self._sct: mss.mss | None = None
        self._roi: dict[str, int] | None = None
        self._template: np.ndarray | None = None
        self._origin: tuple[int, int] | None = None

    def __enter__(self) -> "ScreenTracker":
        self._sct = mss.mss()
        mon = self._sct.monitors[1]  # 主显示器
        cx = mon["left"] + mon["width"] // 2
        cy = mon["top"] + mon["height"] // 2
        self._roi = {
            "left": cx - self.roi_w // 2,
            "top": cy - self.roi_h // 2,
            "width": self.roi_w,
            "height": self.roi_h,
        }
        return self

    def __exit__(self, *exc) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None

    def _grab(self) -> np.ndarray:
        assert self._sct is not None and self._roi is not None
        shot = self._sct.grab(self._roi)
        img = np.array(shot)[:, :, :3]  # BGRA → BGR
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def calibrate(self) -> bool:
        """截取当前中心画面作为参照模板（在按住左键瞬间调用）"""
        frame = self._grab()
        h, w = frame.shape
        ts = self.template_size
        x0 = w // 2 - ts // 2
        y0 = h // 2 - ts // 2
        self._template = frame[y0 : y0 + ts, x0 : x0 + ts].copy()
        self._origin = (x0, y0)
        return True

    def sample(self) -> tuple[float, float] | None:
        """采样一次，返回 (dx, dy) 像素漂移；跟踪丢失返回 None"""
        if self._template is None or self._origin is None:
            return None
        frame = self._grab()
        res = cv2.matchTemplate(frame, self._template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < self.min_confidence:
            return None
        dx = float(max_loc[0] - self._origin[0])
        dy = float(max_loc[1] - self._origin[1])
        return dx, dy


# ---------------------------------------------------------------------------
# SendInput 补偿器
# ---------------------------------------------------------------------------

_MOUSEEVENTF_MOVE = 0x0001


def _move_mouse_raw(dx: int, dy: int) -> None:
    """以原始鼠标像素移动（SendInput/mouse_event，PUBG 可接收）"""
    ctypes.windll.user32.mouse_event(_MOUSEEVENTF_MOVE, dx, dy, 0, 0)


class SendInputCompensator:
    """按住左键期间按射击间隔逐发向下补偿（raw 鼠标像素域）"""

    def __init__(self, per_bullet_px: list[float], interval_ms: float) -> None:
        self.per_bullet_px = per_bullet_px
        self.interval_s = interval_ms / 1000.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self) -> None:
        t0 = time.perf_counter()
        carry = 0.0  # 小数像素累积，避免取整丢量
        for k, px in enumerate(self.per_bullet_px, start=1):
            if self._stop.is_set():
                break
            target = t0 + k * self.interval_s
            while True:
                remain = target - time.perf_counter()
                if remain <= 0:
                    break
                if remain > 0.002:
                    time.sleep(remain - 0.001)
                # 最后 2ms 自旋等待，保证节拍精度
            if px > 0:
                carry += px
                move = int(carry)
                if move > 0:
                    carry -= move
                    _move_mouse_raw(0, move)


# ---------------------------------------------------------------------------
# 扫射记录
# ---------------------------------------------------------------------------


@dataclass
class SpraySession:
    """一次扫射的漂移轨迹"""

    samples: list[tuple[float, float, float]] = field(default_factory=list)
    # (t_ms, dx, dy)，t=0 为按下左键时刻

    @property
    def duration_ms(self) -> float:
        return self.samples[-1][0] if self.samples else 0.0


class SprayRecorder:
    """监听左键，按压期间高频采样 tracker

    短点击过滤：用户确认监听后往往需要先点击游戏窗口获取焦点，
    这一下短点击不能当成扫射——不足 min_hold_ms 的按压会被丢弃并继续监听，
    直到录到一次真正的长按扫射。
    """

    def __init__(self, tracker: ScreenTracker, log_fn=None) -> None:
        self._tracker = tracker
        self._log = log_fn or (lambda msg: None)

    def record_one(
        self,
        compensator: SendInputCompensator | None = None,
        max_seconds: float = 20.0,
        sample_interval_s: float = 0.004,
        min_hold_ms: float = 500.0,
    ) -> SpraySession | None:
        """阻塞等待一次有效扫射（长按 ≥min_hold_ms），返回轨迹；超时返回 None

        短按压（切窗点击、误触）会被忽略并继续监听。
        """
        pressed = threading.Event()
        released = threading.Event()

        def on_click(x, y, button, is_pressed):
            if button == mouse.Button.left:
                if is_pressed:
                    pressed.set()
                elif pressed.is_set():
                    released.set()

        listener = self._create_listener(on_click)
        listener.start()
        try:
            deadline = time.perf_counter() + max_seconds
            while True:
                remain = deadline - time.perf_counter()
                if remain <= 0:
                    return None
                session = self._record_single_press(
                    pressed, released, compensator, remain, sample_interval_s
                )
                if session is None:
                    return None  # 超时
                if session.duration_ms >= min_hold_ms and len(session.samples) >= 5:
                    return session
                self._log(
                    f"  检测到 {session.duration_ms:.0f}ms 短按压（切窗点击？），"
                    "已忽略，继续监听……"
                )
        finally:
            listener.stop()

    @staticmethod
    def _create_listener(on_click):
        """创建鼠标监听器（独立方法便于测试替换）"""
        return mouse.Listener(on_click=on_click)

    def _record_single_press(
        self,
        pressed: threading.Event,
        released: threading.Event,
        compensator: SendInputCompensator | None,
        timeout_s: float,
        sample_interval_s: float,
    ) -> SpraySession | None:
        """录制一次按压（按下→松开），无论长短；超时返回 None"""
        pressed.clear()
        released.clear()
        if not pressed.wait(timeout=timeout_s):
            return None
        t0 = time.perf_counter()
        self._tracker.calibrate()
        if compensator is not None:
            compensator.start()
        session = SpraySession()
        try:
            while not released.is_set():
                if time.perf_counter() - t0 > timeout_s:
                    break
                pos = self._tracker.sample()
                t_ms = (time.perf_counter() - t0) * 1000.0
                if pos is not None:
                    session.samples.append((t_ms, pos[0], pos[1]))
                time.sleep(sample_interval_s)
        finally:
            if compensator is not None:
                compensator.stop()
        return session


# ---------------------------------------------------------------------------
# 逐发切分与平滑
# ---------------------------------------------------------------------------


def _interp_at(samples: list[tuple[float, float, float]], t_ms: float) -> tuple[float, float]:
    """在轨迹上线性插值 t_ms 时刻的 (dx, dy)"""
    if not samples:
        return 0.0, 0.0
    ts = np.array([s[0] for s in samples])
    dxs = np.array([s[1] for s in samples])
    dys = np.array([s[2] for s in samples])
    return float(np.interp(t_ms, ts, dxs)), float(np.interp(t_ms, ts, dys))


def cumulative_recoil(
    sessions: list[SpraySession],
    interval_ms: float,
    n_bullets: int,
) -> tuple[np.ndarray, np.ndarray]:
    """把多次扫射轨迹切成逐发累计漂移（多梭取中位数）

    Returns:
        (cum_dy, cum_dx): 长度 n_bullets+1，索引 0 为第 1 发前（=0），
        索引 k 为第 k 发后的累计屏幕像素漂移（dy>0 需下压）。
    """
    per_session_y: list[np.ndarray] = []
    per_session_x: list[np.ndarray] = []
    for s in sessions:
        if len(s.samples) < 5:
            continue
        ys = [0.0]
        xs = [0.0]
        usable = min(n_bullets, int(s.duration_ms / interval_ms))
        for k in range(1, usable + 1):
            # 第 1 发在 t≈0 击发，第 k 发后的稳定采样点取相邻两发的中点，
            # 避免正好落在击发瞬间被前后采样平均掉一半
            dx, dy = _interp_at(s.samples, (k - 0.5) * interval_ms)
            ys.append(dy)
            xs.append(dx)
        if len(ys) > 2:
            per_session_y.append(np.array(ys))
            per_session_x.append(np.array(xs))

    if not per_session_y:
        return np.zeros(n_bullets + 1), np.zeros(n_bullets + 1)

    # 各梭有效长度可能不同：按共同长度截断后取中位数
    min_len = min(len(a) for a in per_session_y)
    stack_y = np.stack([a[:min_len] for a in per_session_y])
    stack_x = np.stack([a[:min_len] for a in per_session_x])
    med_y = np.median(stack_y, axis=0)
    med_x = np.median(stack_x, axis=0)
    # 不足 n_bullets 的部分用最后值外推
    if min_len < n_bullets + 1:
        pad = n_bullets + 1 - min_len
        med_y = np.concatenate([med_y, np.full(pad, med_y[-1])])
        med_x = np.concatenate([med_x, np.full(pad, med_x[-1])])
    return med_y, med_x


def cumulative_to_per_bullet(cum: np.ndarray) -> np.ndarray:
    """累计曲线 → 逐发增量（裁剪负值：垂直后坐力恒向上）"""
    deltas = np.diff(cum)
    deltas[deltas < 0] = 0.0
    return deltas


def smooth_deltas(deltas: np.ndarray, window: int = 3, keep_first: int = 2) -> np.ndarray:
    """对逐发增量做滑动平均平滑；前 keep_first 发（首发上跳）不平滑"""
    if window < 3 or len(deltas) <= keep_first + 1:
        return deltas
    out = deltas.copy()
    kernel = np.ones(window) / window
    tail = np.convolve(deltas[keep_first:], kernel, mode="same")
    # 边界卷积不准，首尾各回退一个半窗
    half = window // 2
    tail[:half] = deltas[keep_first : keep_first + half]
    tail[-half:] = deltas[-half:]
    out[keep_first:] = tail
    return out


# ---------------------------------------------------------------------------
# ILC 闭环更新
# ---------------------------------------------------------------------------


def estimate_gain(raw_cum: np.ndarray, residual_cum: np.ndarray, applied_cum: np.ndarray) -> float:
    """估计增益 γ（屏幕像素 / 鼠标像素）

    线性模型：residual = raw - γ·applied  →  γ = (raw-residual)·applied / applied·applied
    """
    mask = applied_cum > 1e-6
    if mask.sum() < 3:
        return 1.0
    a = applied_cum[mask]
    b = raw_cum[mask] - residual_cum[mask]
    denom = float(a @ a)
    if denom < 1e-9:
        return 1.0
    gain = float(a @ b) / denom
    return max(0.05, min(gain, 20.0))  # 限制在合理范围防发散


def ilc_update(applied_cum: np.ndarray, residual_cum: np.ndarray, gain: float) -> np.ndarray:
    """把残余误差折算回鼠标像素并叠加到补偿表"""
    updated = applied_cum + residual_cum / gain
    updated[0] = 0.0
    return updated


def residual_rms(residual_cum: np.ndarray) -> float:
    return float(np.sqrt(np.mean(residual_cum[1:] ** 2))) if len(residual_cum) > 1 else 0.0


# ---------------------------------------------------------------------------
# 弹道表生成（自适应分段）
# ---------------------------------------------------------------------------


def build_lua_ballistic(
    per_bullet_px: np.ndarray,
    unit_divisor: float,
    rel_tol: float = 0.08,
    max_chunk: int = 8,
    resolution: float = 0.5,
) -> list[tuple[int, float]]:
    """逐发鼠标像素 → lua ballistic 关键帧表

    Args:
        per_bullet_px: 逐发补偿量（raw 鼠标像素，索引 0 = 第 1 发）
        unit_divisor: 鼠标像素 → lua 单位的除数（(ADS/100) * gunCoeff）
        rel_tol: 段内允许的相对误差
        max_chunk: 单段最多合并发数
        resolution: 输出值的最小粒度（0.5）

    Returns:
        [(bullet_end, value), ...]，首段恒为 (1, 0.0)
    """
    if unit_divisor <= 0:
        unit_divisor = 1.0
    values = per_bullet_px / unit_divisor
    values = np.round(values / resolution) * resolution

    result: list[tuple[int, float]] = [(1, 0.0)]
    i = 1  # 第 2 发起（索引 1）
    n = len(values)
    while i < n:
        j = i
        ref = values[i]
        while j + 1 < n and (j + 1 - i) < max_chunk:
            nxt = values[j + 1]
            base = max(abs(ref), 1.0)
            if abs(nxt - ref) / base > rel_tol:
                break
            j += 1
        seg = values[i : j + 1]
        avg = round(float(seg.mean()) / resolution) * resolution
        result.append((j + 1, round(avg, 2)))
        i = j + 1
    return result


# ---------------------------------------------------------------------------
# 校准主流程
# ---------------------------------------------------------------------------


class CalibrationAborted(Exception):
    """用户中止校准"""


@dataclass
class CalibResult:
    gun: str
    interval_ms: int
    n_bullets: int
    per_bullet_px: np.ndarray
    ballistic: list[tuple[int, float]]
    residual_rms_px: float
    gain: float


class RecoilCalibrator:
    """闭环迭代校准编排"""

    def __init__(
        self,
        gun: str,
        interval_ms: int,
        n_bullets: int,
        lua_path: Path,
        mags_per_round: int = 2,
        converge_rms_px: float = 1.5,
        prompt_fn=None,
        log_fn=None,
        mode: str = "auto",
        write_fn=None,
        tracker_cls=None,
    ) -> None:
        if mode not in ("auto", "manual"):
            raise ValueError(f"未知模式: {mode}")
        self.gun = gun
        self.interval_ms = interval_ms
        self.n_bullets = n_bullets
        self.lua_path = lua_path
        self.mags_per_round = mags_per_round
        self.converge_rms_px = converge_rms_px
        # auto: 本工具 SendInput 实时补偿；manual: 每轮写入 lua，由 GHUB 脚本补偿
        self.mode = mode
        # manual 模式每轮写表回调 write_fn(gun, interval_ms, ballistic)；默认自带序列化
        self._write_fn = write_fn
        self._tracker_cls = tracker_cls or ScreenTracker
        # UI 可注入回调：prompt_fn(msg) 阻塞等待用户确认；log_fn(msg) 输出日志
        self._prompt = prompt_fn or (lambda msg: input(msg))
        self._log = log_fn or print
        self._abort = False

        parser = LuaBallisticParser()
        config = parser.parse(lua_path)
        self._config = config
        gun_info = config.find_gun(gun)
        if gun_info is None:
            raise ValueError(f"canUse 中找不到枪械: {gun}")
        self._gun_coef = gun_info.coef
        # ADS 全局系数（lua: generalSensitivityRatio = ADS/100）
        self._ads_ratio = self._parse_ads_ratio(lua_path)
        self.unit_divisor = self._ads_ratio * self._gun_coef

    def request_abort(self) -> None:
        """请求中止（在梭与轮之间的检查点生效）"""
        self._abort = True

    def set_io(self, prompt_fn=None, log_fn=None) -> None:
        """运行前替换 IO 回调（GUI 集成用；构造后、run() 前调用）"""
        if prompt_fn is not None:
            self._prompt = prompt_fn
        if log_fn is not None:
            self._log = log_fn

    def _make_recorder(self, tracker) -> SprayRecorder:
        """创建扫射记录器（独立方法便于测试替换）"""
        return SprayRecorder(tracker, log_fn=self._log)

    def _write_table(self, ballistic: list[tuple[int, float]]) -> None:
        """manual 模式每轮写回弹道表（含 .bak 备份，与编辑器保存同一套序列化）"""
        if self._write_fn is not None:
            self._write_fn(self.gun, self.interval_ms, ballistic)
            return
        gun_info = self._config.find_gun(self.gun)
        gun_info.interval = self.interval_ms
        gun_info.ballistic = ballistic
        LuaBallisticParser().serialize(self._config, self.lua_path, backup=True)

    def _find_gun_coeff(self, gun: str) -> float:
        gun_info = self._config.find_gun(gun)
        if gun_info is None:
            raise ValueError(f"canUse 中找不到枪械: {gun}")
        return gun_info.coef

    @staticmethod
    def _parse_ads_ratio(lua_path: Path) -> float:
        import re

        content = lua_path.read_text(encoding="utf-8")
        m = re.search(r"ADS\s*=\s*([\d.]+)\s*,", content)
        return float(m.group(1)) / 100.0 if m else 1.0

    def _record_round(
        self,
        recorder: SprayRecorder,
        compensator_px: np.ndarray | None,
        label: str,
    ) -> list[SpraySession]:
        sessions: list[SpraySession] = []
        for m in range(self.mags_per_round):
            if self._abort:
                raise CalibrationAborted()
            self._log(f"[{label}] 第 {m + 1}/{self.mags_per_round} 梭")
            self._prompt(
                "瞄准墙面固定参照物后点击确认。建议用 Alt+Tab 切回游戏"
                "（点鼠标切窗会误触射击）；不足 0.5 秒的短按压会被自动忽略，"
                "按住左键打满整匣后松开。"
            )
            comp = None
            if compensator_px is not None and compensator_px.sum() > 0:
                comp = SendInputCompensator(list(compensator_px), self.interval_ms)
            session = recorder.record_one(compensator=comp, max_seconds=60)
            if session is None or len(session.samples) < 5:
                self._log("  未检测到扫射，本梭作废，请重试。")
                continue
            fired = int(session.duration_ms / self.interval_ms)
            self._log(f"  记录到 {len(session.samples)} 个采样点，约 {fired} 发。")
            if fired < self.n_bullets * 0.8:
                self._log(f"  注意：未达到 {self.n_bullets} 发，尾段数据将外推。")
            sessions.append(session)
        return sessions

    def run(self, max_rounds: int = 4) -> CalibResult | None:
        self._log("=" * 50)
        self._log(f"闭环弹道校准：{self.gun}")
        self._log(f"  射击间隔 {self.interval_ms}ms | 目标 {self.n_bullets} 发")
        self._log(
            f"  单位换算除数 {self.unit_divisor:.3f}"
            f" (ADS比 {self._ads_ratio:.2f} × 系数 {self._gun_coef:.2f})"
        )
        self._log("  请保持：站立 + 红点/全息，与 lua 基准系数一致。")
        self._log("=" * 50)

        with self._tracker_cls() as tracker:
            recorder = self._make_recorder(tracker)

            # 第 0 轮：裸枪测原始后坐力
            self._log("【第 0 轮】裸枪测量（不施加任何补偿）")
            if self.mode == "manual":
                self._log("  请确认 GHUB 压枪脚本处于【关闭】状态。")
            raw_sessions = self._record_round(recorder, None, "裸枪")
            if not raw_sessions:
                self._log("没有有效测量数据，终止。")
                return None
            raw_cum, raw_cum_x = cumulative_recoil(
                raw_sessions, self.interval_ms, self.n_bullets
            )
            self._log(
                f"  原始后坐力：垂直累计 {raw_cum[-1]:.1f}px，"
                f"水平漂移 {abs(raw_cum_x[-1]):.1f}px"
            )

            # 健全性检查：裸枪垂直后坐力接近 0，测量必然失败，直接诊断
            if raw_cum[-1] < 20.0:
                self._log("  测到的垂直后坐力过低，无法校准。常见原因：")
                self._log("  ① 下意识手动压枪——扫射时手轻扶鼠标、不要下拉；")
                self._log("  ② 参照物特征太弱/烟雾遮挡导致模板跟丢——")
                self._log("     换有纹理的参照点（靶心、涂鸦、砖缝交点）；")
                self._log("  ③ GHUB 脚本没关干净，仍在替你压枪。")
                return None

            # 迭代轮
            applied_cum = raw_cum.copy()  # 初始猜测：增益 1
            gain = 1.0
            residual = raw_cum
            for rnd in range(1, max_rounds + 1):
                if self._abort:
                    raise CalibrationAborted()
                per_bullet = cumulative_to_per_bullet(applied_cum)
                if self.mode == "manual":
                    # 把当前补偿表写入 lua，由 GHUB 脚本执行压枪
                    ballistic = build_lua_ballistic(per_bullet, self.unit_divisor)
                    self._write_table(ballistic)
                    self._log(
                        f"【第 {rnd} 轮】已写入第 {rnd} 版弹道到 lua（含 .bak 备份）"
                    )
                    self._prompt(
                        "请在 GHUB 中重新载入/激活压枪脚本，确认脚本已开启且"
                        "识别到当前枪械后，点击确认开始扫射。"
                    )
                    sessions = self._record_round(recorder, None, f"第{rnd}轮")
                else:
                    self._log(f"【第 {rnd} 轮】带补偿复测（本工具实时压枪）")
                    sessions = self._record_round(recorder, per_bullet, f"第{rnd}轮")
                if not sessions:
                    self._log("没有有效测量数据，终止。")
                    return None
                residual, res_x = cumulative_recoil(
                    sessions, self.interval_ms, self.n_bullets
                )
                rms = residual_rms(residual)
                self._log(
                    f"  残余 RMS = {rms:.2f}px（垂直），水平残余 {abs(res_x[-1]):.1f}px"
                )

                # 注入自检：补偿打出去但屏幕纹丝不动
                if applied_cum[-1] > 30.0:
                    response = (raw_cum[-1] - residual[-1]) / applied_cum[-1]
                    if response < 0.05:
                        if self.mode == "manual":
                            self._log("  警告：补偿几乎无效（响应率 <5%），")
                            self._log("  GHUB 脚本可能未重载、未开启，或未识别到枪械。")
                        else:
                            self._log("  警告：补偿注入几乎无效（响应率 <5%），")
                            self._log("  PUBG 可能拦截了 SendInput，请改用 GHUB 手动模式。")
                        return None

                if rms <= self.converge_rms_px:
                    self._log(f"  已收敛（≤{self.converge_rms_px}px）。")
                    break

                if rnd == 1:
                    gain = estimate_gain(raw_cum, residual, applied_cum)
                    self._log(f"  估计增益 γ = {gain:.3f}（屏幕px/鼠标px）")
                applied_cum = ilc_update(applied_cum, residual, gain)
            else:
                self._log(f"达到最大轮次，最终残余 RMS = {residual_rms(residual):.2f}px")

        per_bullet_final = smooth_deltas(cumulative_to_per_bullet(applied_cum))
        ballistic = build_lua_ballistic(per_bullet_final, self.unit_divisor)

        # manual 模式：最终版再写一次（收敛跳出时表已是最新；达到最大轮次时
        # applied_cum 在最后一次写入后又有更新，需要补写）
        if self.mode == "manual":
            self._write_table(ballistic)
            self._log("最终版弹道已写入 lua（含 .bak 备份）。")

        return CalibResult(
            gun=self.gun,
            interval_ms=self.interval_ms,
            n_bullets=self.n_bullets,
            per_bullet_px=per_bullet_final,
            ballistic=ballistic,
            residual_rms_px=residual_rms(residual),
            gain=gain,
        )

    def write_to_lua(self, result: CalibResult, backup: bool = True) -> None:
        """把校准结果写回 lua 配置（更新 interval 与 ballistic）"""
        gun_info = self._config.find_gun(result.gun)
        if gun_info is None:
            raise ValueError(f"canUse 中找不到枪械: {result.gun}")
        gun_info.interval = result.interval_ms
        gun_info.ballistic = result.ballistic
        LuaBallisticParser().serialize(self._config, self.lua_path, backup=backup)
        print(f"已写回 {self.lua_path}（备份 .bak）")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="PUBG 闭环弹道自动校准器")
    ap.add_argument("--gun", required=True, help="枪械名（需与 canUse 中一致），如 RPD")
    ap.add_argument("--interval", type=int, default=0, help="射击间隔 ms（默认按内置 RPM 表）")
    ap.add_argument("--bullets", type=int, default=110, help="整匣发数（RPD 扩容 110）")
    ap.add_argument("--lua", default="pubg_config.lua", help="目标 lua 配置路径")
    ap.add_argument("--mags", type=int, default=2, help="每轮扫射梭数（取中位数抗水平随机）")
    ap.add_argument("--rounds", type=int, default=4, help="最大迭代轮次")
    ap.add_argument(
        "--mode",
        choices=["auto", "manual"],
        default="auto",
        help="auto=本工具 SendInput 实时补偿；manual=每轮写入 lua 由 GHUB 脚本补偿",
    )
    ap.add_argument("--dry-run", action="store_true", help="只打印结果不写 lua")
    args = ap.parse_args(argv)

    interval = args.interval or rpm_to_interval_ms(
        GUN_RPM.get(args.gun, 750)
    )
    lua_path = Path(args.lua).resolve()
    if not lua_path.exists():
        print(f"lua 文件不存在: {lua_path}")
        return 1

    cal = RecoilCalibrator(
        gun=args.gun,
        interval_ms=interval,
        n_bullets=args.bullets,
        lua_path=lua_path,
        mags_per_round=args.mags,
        mode=args.mode,
    )
    result = cal.run(max_rounds=args.rounds)
    if result is None:
        return 1

    print("\n" + "=" * 60)
    print("校准完成，生成的弹道表：")
    print(f"  interval = {result.interval_ms},")
    for num, val in result.ballistic:
        print(f"  {{{num}, {val}}},")
    print(f"最终残余 RMS: {result.residual_rms_px:.2f}px | 增益 γ: {result.gain:.3f}")
    print("=" * 60)

    if args.dry_run:
        print("dry-run，未写回。")
        return 0
    if args.mode == "manual":
        print("manual 模式：弹道已在各轮迭代中写回 lua。")
        return 0
    ans = input("写回 lua 配置？[y/N] ").strip().lower()
    if ans == "y":
        cal.write_to_lua(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
