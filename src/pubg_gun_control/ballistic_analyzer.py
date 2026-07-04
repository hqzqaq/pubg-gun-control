"""
弹道分析工具

从弹孔截图（绿色弹孔标记）自动提取弹道数据，生成 Lua 压枪参数。
移植自 recoil_control 项目，适配 pubg-gun-control 的 Lua 格式。

@author hqzqaq
@since 2026-06-25
@version 1.0
"""

import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    from skimage.feature import blob_log
    _HAS_SKIMAGE = True
except ImportError:
    _HAS_SKIMAGE = False


def _greenness_image(hsv, h_range=(30, 95), s_min=15):
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    green = ((h >= h_range[0]) & (h <= h_range[1]) & (s >= s_min)).astype(np.float64)
    return (v.astype(np.float64) / 255.0) * green


def _split_blob_into_peaks(greenness, cx, cy, sigma, radius_scale=2.5, thresh_ratio=0.02):
    h, w = greenness.shape
    r = max(5, int(radius_scale * sigma))
    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
    patch = greenness[y0:y1, x0:x1].copy()
    if patch.max() < 1e-6:
        return [(cx, cy)]
    _, binary = cv2.threshold(
        (patch * 255).astype(np.uint8), max(1, int(255 * thresh_ratio)), 255, cv2.THRESH_BINARY
    )
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    max_d = dist.max()
    if max_d < 1e-6:
        return [(cx, cy)]
    _, peak_mask = cv2.threshold(dist, max(1.0, max_d * 0.4), 255, cv2.THRESH_BINARY)
    peak_mask = np.uint8(peak_mask)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(peak_mask)
    out = []
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < 2:
            continue
        ys, xs = np.where(labels == i)
        px = int(x0 + np.mean(xs))
        py = int(y0 + np.mean(ys))
        out.append((px, py))
    return out if len(out) >= 2 else [(cx, cy)]


def _extract_green_points_blob_log(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    greenness = _greenness_image(hsv, s_min=15)
    if greenness.max() < 1e-6:
        return []
    greenness = cv2.GaussianBlur(greenness, (5, 5), 1.0)
    blobs = blob_log(greenness, min_sigma=2, max_sigma=12, num_sigma=10, threshold=0.02, overlap=0.0)
    if len(blobs) == 0:
        return []
    points = []
    for b in blobs:
        by, bx, sigma = b[0], b[1], b[2]
        cx, cy = int(bx), int(by)
        if sigma > 6.0:
            for (px, py) in _split_blob_into_peaks(greenness, cx, cy, sigma):
                points.append((px, py))
        else:
            points.append((cx, cy))
    points.sort(key=lambda p: p[1], reverse=True)
    return points


def _extract_green_points_opencv(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([30, 80, 60]), np.array([95, 255, 255]))
    kernel = np.ones((2, 2), np.uint8)
    mask_sep = cv2.erode(mask, kernel)
    contours, _ = cv2.findContours(mask_sep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    points = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 3:
            continue
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            points.append((cx, cy))
    points.sort(key=lambda p: p[1], reverse=True)
    return points


def extract_green_points(img):
    """从 BGR 图像中提取弹孔坐标，按 y 从下往上排序（先打的在前）

    支持两种弹孔类型：
    1. 绿色标记点（训练场overlay标记）
    2. 灰色/黑色弹孔（对墙射击的真实弹痕）
    """
    # 策略1: 尝试灰色弹孔检测（对墙射击，最常见的场景）
    gray_points = _extract_gray_holes(img)
    if len(gray_points) >= 5:
        return gray_points

    # 策略2: 尝试绿色点检测（训练场overlay标记）
    if _HAS_SKIMAGE:
        green_points = _extract_green_points_blob_log(img)
        if len(green_points) >= 5:
            return green_points

    # 策略3: 如果灰色检测找到一些但不够多，也返回
    if len(gray_points) >= 2:
        return gray_points

    # 策略4: OpenCV绿色轮廓检测（回退）
    return _extract_green_points_opencv(img)


def _extract_gray_holes(img):
    """提取灰色/黑色弹孔（对墙射击的真实弹痕）

    策略：先定位弹道垂直条带，再在条带内用阈值分割找弹孔
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)

    # 第一步：用全局阈值找所有暗色像素，投影到 x 轴找到弹道中心
    _, binary_global = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    x_projection = binary_global.sum(axis=0)

    # 找到暗色像素最集中的 x 区域（弹道所在列）
    window = max(10, w // 8)
    best_x, best_sum = 0, 0
    for x in range(w):
        x_start = max(0, x - window // 2)
        x_end = min(w, x + window // 2)
        s = x_projection[x_start:x_end].sum()
        if s > best_sum:
            best_sum = s
            best_x = x

    # 弹道条带范围
    strip_half = max(60, window)
    strip_x0 = max(0, best_x - strip_half)
    strip_x1 = min(w, best_x + strip_half)

    # 第二步：在弹道条带内用较低阈值分割
    strip = blurred[:, strip_x0:strip_x1]

    # 使用条带内较暗的像素百分位数作为阈值
    strip_sorted = np.sort(strip.flatten())
    thresh_idx = int(len(strip_sorted) * 0.35)
    thresh_val = max(30, strip_sorted[thresh_idx])

    _, binary_strip = cv2.threshold(strip, thresh_val, 255, cv2.THRESH_BINARY_INV)

    # 形态学操作：闭合弹孔内部空洞
    kernel = np.ones((3, 3), np.uint8)
    binary_strip = cv2.morphologyEx(binary_strip, cv2.MORPH_CLOSE, kernel)
    binary_strip = cv2.morphologyEx(binary_strip, cv2.MORPH_OPEN, kernel)

    # 找轮廓
    contours, _ = cv2.findContours(binary_strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 弹孔面积范围
    min_area = 10
    max_area = 600

    points = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.15:
            continue
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) + strip_x0
            cy = int(M["m01"] / M["m00"])
            points.append((cx, cy))

    # 第三步：过滤掉离弹道中心线太远的点
    if points:
        avg_x = np.mean([p[0] for p in points])
        max_deviation = max(50, w * 0.2)
        points = [p for p in points if abs(p[0] - avg_x) < max_deviation]

    points.sort(key=lambda p: p[1], reverse=True)
    return points


def points_to_cumulative_y(points, scale=1.0):
    """将弹孔坐标转换为累计垂直偏移量（用于 pubg-gun-control 的 Lua 格式）

    Args:
        points: 弹孔坐标列表 [(x, y), ...]，按射击顺序排列
        scale: 缩放系数

    Returns:
        list of (bullet_num, cumulative_y) 表示每发子弹的累计垂直偏移
    """
    if len(points) < 2:
        return []

    result = [(1, 0)]
    cumulative_y = 0.0
    for i in range(1, len(points)):
        dy = abs(points[i][1] - points[i - 1][1])
        cumulative_y += dy * scale
        result.append((i + 1, round(cumulative_y, 1)))

    return result


def segments_to_ballistic(points, scale=0.7, max_seg_count=5):
    """将弹孔坐标转换为 pubg-gun-control 格式的弹道数据

    输出格式: [(bullet_num, vertical_offset), ...]
    与 Lua 脚本中 pubg["GunName"] 的 ballistic 表一致

    Args:
        points: 弹孔坐标列表
        scale: 坐标缩放系数
        max_seg_count: 单段最大子弹数

    Returns:
        list of (bullet_num, offset) 元组
    """
    if len(points) < 2:
        return []

    raw_deltas = []
    for i in range(1, len(points)):
        dy = abs(points[i][1] - points[i - 1][1])
        raw_deltas.append(round(dy * scale, 1))

    segments = []
    current_sum = raw_deltas[0]
    current_count = 1

    for i in range(1, len(raw_deltas)):
        if current_count >= max_seg_count:
            segments.append(round(current_sum / current_count, 1))
            current_sum = raw_deltas[i]
            current_count = 1
        else:
            current_sum += raw_deltas[i]
            current_count += 1
    segments.append(round(current_sum / current_count, 1))

    result = [(1, 0)]
    bullet_num = 2
    for offset in segments:
        result.append((bullet_num, offset))
        bullet_num += 1

    return result


def analyze_spray_image(image_path, scale=0.7, max_seg_count=5):
    """分析弹孔截图，返回弹道数据

    Args:
        image_path: 截图路径
        scale: 缩放系数
        max_seg_count: 每段最大子弹数

    Returns:
        dict: {"points": [...], "ballistic": [(num, offset), ...], "shot_count": int}
    """
    img = cv2.imread(image_path)
    if img is None:
        logger.error("无法读取图片: %s", image_path)
        return None

    points = extract_green_points(img)
    if len(points) < 2:
        logger.error("有效弹孔不足2个，无法分析")
        return None

    ballistic = segments_to_ballistic(points, scale, max_seg_count)

    logger.info("识别到 %d 个弹孔，生成 %d 段弹道数据", len(points), len(ballistic))

    return {
        "points": points,
        "ballistic": ballistic,
        "shot_count": len(points),
    }


def format_lua_function(gun_name, ballistic, interval=87):
    """将弹道数据格式化为 Lua 函数字符串

    Args:
        gun_name: 枪械名称
        ballistic: [(bullet_num, offset), ...]
        interval: 射击间隔(ms)

    Returns:
        str: Lua 函数代码
    """
    lines = [f'pubg["{gun_name}"] = function (gunName)', '']
    lines.append('\treturn pubg.execOptions(gunName, {')
    lines.append(f'\t\tinterval = {interval},')
    lines.append('\t\tballistic = {')

    for num, offset in ballistic:
        lines.append(f'\t\t\t{{{num}, {offset}}},')

    lines.append('\t\t}')
    lines.append('\t})')
    lines.append('')
    lines.append('end')

    return "\n".join(lines)
