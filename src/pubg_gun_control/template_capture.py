"""
模板采集工具

引导用户在游戏中切换到指定枪械/配件，截取 ROI 区域保存为参考模板。
枪口配件按武器类型（步枪/冲锋枪）分别采集，握把和枪托共用模板。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
import time
import tkinter as tk
from typing import Callable

import cv2
import mss
import numpy as np

from pubg_gun_control.recognizer import GUN_NAMES, MUZZLE_OPTIONS, MUZZLE_OPTIONS_SMG, GRIP_OPTIONS, STOCK_OPTIONS, GUN_TYPE_LABELS

logger = logging.getLogger(__name__)

SCOPE_OPTIONS = [
    (1, "ironsight", "机瞄"),
    (1, "reddot", "红点瞄准镜"),
    (1, "holo", "全息瞄准镜"),
    (2, "2x", "2倍镜"),
    (3, "3x", "3倍镜"),
]


def _capture_roi(roi: list[int]) -> np.ndarray:
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        frame = np.array(sct_img)[:, :, :3]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    x1, y1, x2, y2 = roi
    return frame[y1:y2, x1:x2]


class TemplateCaptureUI:
    """模板采集向导界面，支持返回上一步"""

    def __init__(
        self,
        roi: list[int],
        items: list[dict],
        on_complete: Callable[[list[dict]], None],
        title: str = "采集模板",
    ) -> None:
        """
        Args:
            roi: 截图区域 [x1, y1, x2, y2]
            items: 待采集列表, 每项 {"name": str, "label": str, "image": np.ndarray|None}
            on_complete: 完成回调, 传入采集结果列表
            title: 窗口标题
        """
        self._roi = roi
        self._items = [dict(item) for item in items]
        self._on_complete = on_complete
        self._title = title
        self._current = 0

    def start(self) -> None:
        self._root = tk.Tk()
        self._root.title(self._title)
        self._root.attributes("-topmost", True)
        self._root.geometry("450x250")
        self._root.resizable(False, False)

        self._hint_label = tk.Label(
            self._root, text="", font=("Microsoft YaHei", 12), wraplength=430,
        )
        self._hint_label.pack(pady=(20, 10))

        self._status_label = tk.Label(
            self._root, text="", font=("Microsoft YaHei", 10), fg="green",
        )
        self._status_label.pack(pady=5)

        btn_frame = tk.Frame(self._root)
        btn_frame.pack(pady=10)

        self._back_btn = tk.Button(
            btn_frame, text="← 上一步", font=("Microsoft YaHei", 10),
            command=self._on_back, width=10, state=tk.DISABLED,
        )
        self._back_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="截图采集", font=("Microsoft YaHei", 10, "bold"),
            command=self._on_capture, width=10,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="跳过", font=("Microsoft YaHei", 10),
            command=self._on_skip, width=8,
        ).pack(side=tk.LEFT, padx=5)

        self._update_display()
        self._root.mainloop()

    def _update_display(self) -> None:
        total = len(self._items)
        item = self._items[self._current]
        label = item["label"]
        status = f"[{self._current + 1}/{total}]"

        self._hint_label.config(text=f"{status} 请装备: {label}")

        if item["image"] is not None:
            h, w = item["image"].shape[:2]
            self._status_label.config(text=f"✓ 已截取 ({w}x{h})", fg="green")
        else:
            self._status_label.config(text="尚未截取", fg="gray")

        self._back_btn.config(state=tk.NORMAL if self._current > 0 else tk.DISABLED)

    def _on_capture(self) -> None:
        self._root.withdraw()
        time.sleep(0.5)
        img = _capture_roi(self._roi)
        self._items[self._current]["image"] = img
        self._root.deiconify()
        h, w = img.shape[:2]
        self._status_label.config(text=f"✓ 已截取 ({w}x{h})", fg="green")
        self._auto_next()

    def _on_skip(self) -> None:
        self._items[self._current]["image"] = None
        self._auto_next()

    def _on_back(self) -> None:
        if self._current > 0:
            self._current -= 1
            self._update_display()

    def _auto_next(self) -> None:
        self._current += 1
        if self._current >= len(self._items):
            self._finish()
        else:
            self._update_display()

    def _finish(self) -> None:
        self._root.destroy()
        self._on_complete(self._items)


def capture_gun_templates(
    weapon_roi: list[int],
    save_fn: Callable[[str, np.ndarray], None],
    gun_names: list[str] | None = None,
) -> int:
    """逐个采集枪械名称模板"""
    if gun_names is None:
        gun_names = GUN_NAMES

    items = [{"name": gun, "label": gun, "image": None} for gun in gun_names]
    captured = 0

    def on_done(result_items: list[dict]) -> None:
        nonlocal captured
        for item in result_items:
            if item["image"] is not None:
                save_fn(item["name"], item["image"])
                captured += 1

    TemplateCaptureUI(
        roi=weapon_roi, items=items, on_complete=on_done, title="采集枪械模板",
    ).start()
    return captured


def capture_muzzle_templates(
    roi: list[int],
    save_fn: Callable[[str, str, np.ndarray, str], None],
    weapon_type: str = "ar",
) -> int:
    """采集某个武器类型的枪口配件模板（跳过"无"）"""
    options = MUZZLE_OPTIONS_SMG if weapon_type == "smg" else MUZZLE_OPTIONS
    labels_map = {
        "none": "无", "comp": "补偿器", "flash": "消焰器",
        "silencer": "消音器", "brake": "制退器",
    }
    type_label = GUN_TYPE_LABELS.get(weapon_type, weapon_type)

    items = []
    for name in options:
        if name == "none":
            continue
        items.append({"name": name, "label": f"【{type_label}】{labels_map.get(name, name)}", "image": None})

    captured = 0

    def on_done(result_items: list[dict]) -> None:
        nonlocal captured
        for item in result_items:
            if item["image"] is not None:
                save_fn("muzzle", item["name"], item["image"], weapon_type)
                captured += 1

    TemplateCaptureUI(
        roi=roi, items=items, on_complete=on_done, title=f"采集{type_label}枪口模板",
    ).start()
    return captured


def capture_shared_attachment_templates(
    roi: list[int],
    category: str,
    save_fn: Callable[[str, str, np.ndarray], None],
) -> int:
    """采集握把或枪托的共用模板（跳过"无"）"""
    options = {"grip": GRIP_OPTIONS, "stock": STOCK_OPTIONS}[category]
    labels_map = {
        "grip": {"none": "无", "vertical": "垂直握把", "laser": "斜向握把",
                 "thumb": "拇指握把", "half": "半截式握把", "lightgrip": "轻型握把"},
        "stock": {"none": "无", "tactical": "战术枪托", "heavy": "重型枪托"},
    }[category]
    cat_label = {"grip": "握把", "stock": "枪托"}[category]

    items = []
    for name in options:
        if name == "none":
            continue
        items.append({"name": name, "label": labels_map.get(name, name), "image": None})

    captured = 0

    def on_done(result_items: list[dict]) -> None:
        nonlocal captured
        for item in result_items:
            if item["image"] is not None:
                save_fn(category, item["name"], item["image"])
                captured += 1

    TemplateCaptureUI(
        roi=roi, items=items, on_complete=on_done, title=f"采集{cat_label}模板",
    ).start()
    return captured


def capture_scope_templates(
    roi: list[int],
    save_fn: Callable[[int, np.ndarray, str], None],
) -> int:
    """采集倍镜模板（机瞄/红点/全息分开采集，只到3倍）"""
    items = []
    for scope_val, eng_name, label in SCOPE_OPTIONS:
        items.append({"name": eng_name, "label": label, "image": None})

    captured = 0

    def on_done(result_items: list[dict]) -> None:
        nonlocal captured
        for item in result_items:
            if item["image"] is not None:
                scope_val = 1
                for sv, en, _ in SCOPE_OPTIONS:
                    if en == item["name"]:
                        scope_val = sv
                        break
                save_fn(scope_val, item["image"], item["name"])
                captured += 1

    TemplateCaptureUI(
        roi=roi, items=items, on_complete=on_done, title="采集倍镜模板",
    ).start()
    return captured
