"""
截图识别引擎

使用 cv2 模板匹配识别枪械名称和配件图标。
配件模板按武器类型分组存储，因为不同武器类型的同名配件图标不同。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

GUN_NAMES = [
    "M416", "Beryl M762", "AKM", "AUG", "SCAR-L", "QBZ", "G36C", "ACE32",
    "UMP45", "MP5K", "Vector", "Micro UZI", "P90", "M249", "M16A4", "Groza",
    "DP-28", "MK47", "Tommy Gun", "Famas", "MG3",
]

GUN_TYPE_MAP: dict[str, str] = {
    "M416": "ar", "Beryl M762": "ar", "AKM": "ar", "AUG": "ar",
    "SCAR-L": "ar", "QBZ": "ar", "G36C": "ar", "ACE32": "ar",
    "M16A4": "ar", "Groza": "ar", "Famas": "ar",
    "UMP45": "smg", "MP5K": "smg", "Vector": "smg", "Micro UZI": "smg", "P90": "smg",
    "M249": "lmg", "DP-28": "lmg", "MG3": "lmg",
    "MK47": "ar",
    "Tommy Gun": "smg",
}

GUN_TYPE_LABELS: dict[str, str] = {
    "ar": "步枪",
    "smg": "冲锋枪",
    "lmg": "机枪",
}

MUZZLE_OPTIONS = ["none", "comp", "flash", "silencer", "brake"]
MUZZLE_OPTIONS_SMG = ["none", "comp", "flash", "silencer"]
GRIP_OPTIONS = ["none", "vertical", "laser", "thumb", "half", "lightgrip"]
STOCK_OPTIONS = ["none", "tactical", "heavy"]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


class GunRecognizer:
    """截图识别枪械名称和配件（全部基于模板匹配）"""

    def __init__(self, rois: dict[str, list[int]], template_dir: str | None = None) -> None:
        self._rois = rois
        self._template_dir = Path(template_dir) if template_dir else TEMPLATE_DIR
        self._gun_templates: dict[str, np.ndarray] = {}
        self._attachment_templates: dict[str, dict[str, dict[str, np.ndarray]]] = {}
        self._scope_templates: dict[str, tuple[np.ndarray, int]] = {}
        self._load_all_templates()

    def _load_all_templates(self) -> None:
        gun_dir = self._template_dir / "guns"
        if gun_dir.exists():
            for img_path in gun_dir.glob("*.png"):
                gun_name = img_path.stem
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self._gun_templates[gun_name] = img
            logger.info("已加载 %d 个枪械模板", len(self._gun_templates))

        self._attachment_templates["muzzle"] = {}
        muzzle_dir = self._template_dir / "muzzle"
        if muzzle_dir.exists():
            for type_dir in muzzle_dir.iterdir():
                if not type_dir.is_dir():
                    continue
                weapon_type = type_dir.name
                self._attachment_templates["muzzle"][weapon_type] = {}
                for img_path in type_dir.glob("*.png"):
                    name = img_path.stem
                    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self._attachment_templates["muzzle"][weapon_type][name] = img

        for category in ["grip", "stock"]:
            self._attachment_templates[category] = {"_shared": {}}
            cat_dir = self._template_dir / category
            if cat_dir.exists():
                for img_path in cat_dir.glob("*.png"):
                    name = img_path.stem
                    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self._attachment_templates[category]["_shared"][name] = img

        scope_dir = self._template_dir / "scope"
        if scope_dir.exists():
            for img_path in scope_dir.glob("*.png"):
                try:
                    stem = img_path.stem
                    scope_val = int(stem.split("_")[0])
                    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self._scope_templates[stem] = (img, scope_val)
                except (ValueError, IndexError):
                    pass

    def _capture_full_screen(self) -> np.ndarray:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            frame = np.array(sct_img)[:, :, :3]
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def capture_roi(self, roi: list[int], screenshot: np.ndarray | None = None) -> np.ndarray:
        if screenshot is None:
            screenshot = self._capture_full_screen()
        x1, y1, x2, y2 = roi
        return screenshot[y1:y2, x1:x2]

    def _match_template(self, roi_gray: np.ndarray, templates: dict[str, np.ndarray], threshold: float = 0.7) -> tuple[str | None, float]:
        if not templates or roi_gray.size == 0:
            return None, 0.0

        roi_edges = cv2.Canny(roi_gray, 50, 150)

        best_name = None
        best_score = 0.0

        for name, tmpl in templates.items():
            if roi_gray.shape[0] < tmpl.shape[0] or roi_gray.shape[1] < tmpl.shape[1]:
                scale = min(roi_gray.shape[0] / tmpl.shape[0], roi_gray.shape[1] / tmpl.shape[1])
                if scale < 0.5:
                    continue
                new_w = int(tmpl.shape[1] * scale)
                new_h = int(tmpl.shape[0] * scale)
                tmpl = cv2.resize(tmpl, (new_w, new_h), interpolation=cv2.INTER_AREA)

            tmpl_edges = cv2.Canny(tmpl, 50, 150)
            result = cv2.matchTemplate(roi_edges, tmpl_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_name = name

        if best_score >= threshold:
            return best_name, best_score
        return None, best_score

    def recognize_weapon(self, roi_image: np.ndarray) -> str | None:
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY) if len(roi_image.shape) == 3 else roi_image
        name, score = self._match_template(gray, self._gun_templates, threshold=0.5)
        if name:
            logger.debug("枪械识别: %s (置信度: %.2f)", name, score)
        return name

    def get_weapon_type(self, gun_name: str | None) -> str:
        if gun_name and gun_name in GUN_TYPE_MAP:
            return GUN_TYPE_MAP[gun_name]
        return "ar"

    def recognize_attachment(self, roi_image: np.ndarray, category: str, weapon_type: str = "ar") -> int:
        if category == "muzzle":
            type_templates = self._attachment_templates.get(category, {}).get(weapon_type, {})
        else:
            type_templates = self._attachment_templates.get(category, {}).get("_shared", {})

        if not type_templates:
            logger.debug("配件 %s 无模板 (weapon_type=%s)", category, weapon_type)
            return 1

        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY) if len(roi_image.shape) == 3 else roi_image

        thresholds = {"muzzle": 0.25, "grip": 0.3, "stock": 0.35}
        name, score = self._match_template(gray, type_templates, threshold=thresholds.get(category, 0.35))
        logger.debug("配件 %s (type=%s): best=%s score=%.3f roi=%s",
                     category, weapon_type, name, score, gray.shape)
        if name:
            options = {"muzzle": MUZZLE_OPTIONS, "grip": GRIP_OPTIONS, "stock": STOCK_OPTIONS}[category]
            if name in options:
                return options.index(name) + 1
        return 1

        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY) if len(roi_image.shape) == 3 else roi_image

        name, score = self._match_template(gray, type_templates, threshold=0.6)
        if name:
            if category == "muzzle":
                options = MUZZLE_OPTIONS_SMG if weapon_type == "smg" else MUZZLE_OPTIONS
            else:
                options = {"grip": GRIP_OPTIONS, "stock": STOCK_OPTIONS}[category]
            if name in options:
                return options.index(name) + 1
        return 1

    def recognize_scope(self, roi_image: np.ndarray) -> int:
        if not self._scope_templates:
            logger.debug("倍镜: 无模板")
            return 1
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY) if len(roi_image.shape) == 3 else roi_image

        best_name = None
        best_score = 0.0
        for name, (tmpl, scope_val) in self._scope_templates.items():
            if gray.shape[0] < tmpl.shape[0] or gray.shape[1] < tmpl.shape[1]:
                continue
            result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_name = name

        logger.debug("倍镜: best=%s score=%.3f roi=%s", best_name, best_score, gray.shape)
        if best_name and best_score >= 0.35 and best_name in self._scope_templates:
            return self._scope_templates[best_name][1]
        return 1

    def recognize_all(self, screenshot: np.ndarray | None = None) -> dict:
        if screenshot is None:
            screenshot = self._capture_full_screen()

        result: dict = {"gun": None, "muzzle": 1, "grip": 1, "stock": 1, "scope": 1}

        if "weapon_roi" in self._rois:
            roi_img = self.capture_roi(self._rois["weapon_roi"], screenshot)
            result["gun"] = self.recognize_weapon(roi_img)

        weapon_type = self.get_weapon_type(result["gun"])
        result["weapon_type"] = weapon_type

        for category in ["muzzle", "grip", "stock"]:
            roi_key = f"{category}_roi"
            if roi_key in self._rois:
                roi_img = self.capture_roi(self._rois[roi_key], screenshot)
                result[category] = self.recognize_attachment(roi_img, category, weapon_type)

        if "scope_roi" in self._rois:
            roi_img = self.capture_roi(self._rois["scope_roi"], screenshot)
            result["scope"] = self.recognize_scope(roi_img)

        return result

    def save_gun_template(self, gun_name: str, image: np.ndarray) -> None:
        gun_dir = self._template_dir / "guns"
        gun_dir.mkdir(parents=True, exist_ok=True)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        path = gun_dir / f"{gun_name}.png"
        cv2.imwrite(str(path), gray)
        self._gun_templates[gun_name] = gray
        logger.info("枪械模板已保存: %s", path)

    def save_attachment_template(self, category: str, name: str, image: np.ndarray, weapon_type: str = "ar") -> None:
        if category == "muzzle":
            cat_dir = self._template_dir / category / weapon_type
        else:
            cat_dir = self._template_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        path = cat_dir / f"{name}.png"
        cv2.imwrite(str(path), gray)
        if category not in self._attachment_templates:
            self._attachment_templates[category] = {}
        if category == "muzzle":
            if weapon_type not in self._attachment_templates[category]:
                self._attachment_templates[category][weapon_type] = {}
            self._attachment_templates[category][weapon_type][name] = gray
        else:
            if "_shared" not in self._attachment_templates[category]:
                self._attachment_templates[category]["_shared"] = {}
            self._attachment_templates[category]["_shared"][name] = gray
        logger.info("配件模板已保存: %s", path)

    def save_scope_template(self, scope_value: int, image: np.ndarray, label: str = "") -> None:
        scope_dir = self._template_dir / "scope"
        scope_dir.mkdir(parents=True, exist_ok=True)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        filename = f"{scope_value}_{label}" if label else str(scope_value)
        path = scope_dir / f"{filename}.png"
        cv2.imwrite(str(path), gray)
        self._scope_templates[filename] = (gray, scope_value)
        logger.info("倍镜模板已保存: %s", path)

    def has_gun_templates(self) -> bool:
        return len(self._gun_templates) > 0

    def get_captured_types(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for category in ["muzzle", "grip", "stock"]:
            result[category] = list(self._attachment_templates.get(category, {}).keys())
        return result
