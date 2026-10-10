"""
姿态跟踪模块

通过全局键盘监听推断 PUBG 中角色的姿态（站立 / 蹲下 / 趴下），
供压枪脚本按姿态切换后坐力系数。

设计要点
--------
1. Toggle 模式：C / Z 是状态翻转键。用 press / release 配对消除 Windows
   按键自动重复（长按 C 只翻转一次），松开后才能再次触发。
2. 打断键：Space（跳跃、翻越）等会强制角色回到站立，直接重置为 stand。
3. 焦点过滤：仅当 PUBG 处于前台时更新状态，避免在桌面聊天打字时误翻转。
4. 手动纠正：状态可能因被击倒、上下载具、游泳等情况漂移，提供
   set_stance() 供界面手动覆盖。

@author hqzqaq
@since 2026-09-25
@version 1.0
"""

import ctypes
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

STAND: str = "stand"
CROUCH: str = "crouch"
PRONE: str = "prone"

VALID_STANCES: tuple[str, ...] = (STAND, CROUCH, PRONE)

# 悬浮窗上显示的短标签（宽度有限，用单字）
STANCE_LABEL: dict[str, str] = {
    STAND: "站",
    CROUCH: "蹲",
    PRONE: "趴",
}

_PROCESS_QUERY_LIMITED_INFORMATION: int = 0x1000

# 进程名片段（小写，去掉 .exe 后匹配）
_GAME_PROCESS_HINTS: tuple[str, ...] = ("tslgame", "tsl")
# 窗口标题兜底片段（小写）
_GAME_TITLE_HINTS: tuple[str, ...] = ("pubg", "battlegrounds", "绝地求生")

_DEFAULT_BREAK_KEYS: tuple[str, ...] = ("space",)


def _matches_game(process_name: str, title: str) -> bool:
    proc = (process_name or "").lower()
    if proc.endswith(".exe"):
        proc = proc[:-4]
    if any(proc.startswith(hint) for hint in _GAME_PROCESS_HINTS):
        return True

    low_title = (title or "").lower()
    return any(hint in low_title for hint in _GAME_TITLE_HINTS)


def foreground_info() -> tuple[str, str]:
    """返回当前前台窗口的 (进程名, 窗口标题)，获取失败时返回空串。"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""

        length = user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        kernel32 = ctypes.windll.kernel32
        hproc = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not hproc:
            return "", title
        try:
            name_buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.psapi.GetModuleBaseNameW(hproc, None, name_buf, 260)
            return name_buf.value, title
        finally:
            kernel32.CloseHandle(hproc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("读取前台窗口信息失败: %s", exc)
        return "", ""


def is_pubg_foreground() -> bool:
    """判断 PUBG 是否处于前台。

    先按进程名匹配（TslGame*），拿不到进程名时再用窗口标题兜底。
    信息完全读不到时返回 True 降级放行，避免姿态跟踪整体失效。
    """
    try:
        process_name, title = foreground_info()
        if not process_name and not title:
            # 没有任何可用信息（如锁屏、权限不足），放行
            return True
        return _matches_game(process_name, title)
    except Exception as exc:  # noqa: BLE001 - 焦点检测属于增强项，失败不应影响主流程
        logger.debug("前台窗口检测失败，降级放行: %s", exc)
        return True


class StanceTracker:
    """角色姿态状态机"""

    def __init__(
        self,
        enabled: bool = True,
        crouch_key: str = "c",
        prone_key: str = "z",
        break_keys: list[str] | None = None,
        require_focus: bool = True,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        self._enabled: bool = enabled
        self._require_focus: bool = require_focus
        self._on_change: Callable[[str], None] | None = on_change
        self._lock = threading.Lock()

        self._stance: str = STAND
        self._held: set[str] = set()  # 当前按住的键，用于过滤按键重复

        self.update_keys(crouch_key, prone_key, break_keys)

    # ---- 配置 ----

    def update_keys(
        self,
        crouch_key: str,
        prone_key: str,
        break_keys: list[str] | None = None,
    ) -> None:
        """更新蹲下 / 趴下 / 打断键配置"""
        with self._lock:
            self._crouch_key = str(crouch_key or "c").strip().lower()
            self._prone_key = str(prone_key or "z").strip().lower()
            keys = break_keys if break_keys is not None else list(_DEFAULT_BREAK_KEYS)
            self._break_keys: set[str] = {str(k).strip().lower() for k in keys if str(k).strip()}

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def stance(self) -> str:
        with self._lock:
            return self._stance

    # ---- 事件入口 ----

    def on_press(self, key_name: str | None) -> bool:
        """按键按下。返回姿态是否发生变化。"""
        name = self._normalize(key_name)
        if name is None:
            return False

        with self._lock:
            if not self._enabled:
                return False
            # 按住不放时系统会持续重复 keydown，这里只认第一次
            if name in self._held:
                return False
            self._held.add(name)

        if self._require_focus and not is_pubg_foreground():
            return False

        return self._apply_key(name)

    def on_release(self, key_name: str | None) -> None:
        """按键抬起"""
        name = self._normalize(key_name)
        if name is None:
            return
        with self._lock:
            self._held.discard(name)

    def set_stance(self, stance: str) -> bool:
        """手动覆盖姿态（用于界面纠正状态漂移）"""
        if stance not in VALID_STANCES:
            return False
        with self._lock:
            if self._stance == stance:
                return False
            self._stance = stance
        logger.info("姿态手动纠正为: %s", stance)
        self._notify(stance)
        return True

    def reset(self) -> bool:
        """重置为站立"""
        return self.set_stance(STAND)

    # ---- 内部 ----

    @staticmethod
    def _normalize(key_name: str | None) -> str | None:
        if not key_name:
            return None
        name = str(key_name).strip().lower()
        return name or None

    def _apply_key(self, name: str) -> bool:
        with self._lock:
            current = self._stance
            break_keys = self._break_keys
            crouch_key = self._crouch_key
            prone_key = self._prone_key

        if name in break_keys:
            target = STAND
        elif name == crouch_key:
            target = CROUCH if current != CROUCH else STAND
        elif name == prone_key:
            target = CROUCH if current == PRONE else PRONE
        else:
            return False

        with self._lock:
            if self._stance == target:
                return False
            self._stance = target

        logger.info("姿态切换: %s -> %s (key=%s)", current, target, name)
        self._notify(target)
        return True

    def _notify(self, stance: str) -> None:
        if self._on_change is None:
            return
        try:
            self._on_change(stance)
        except Exception as exc:  # noqa: BLE001 - 回调异常不应影响状态机
            logger.exception("姿态变化回调失败: %s", exc)
