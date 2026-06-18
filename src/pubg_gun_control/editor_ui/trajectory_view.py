"""
弹道轨迹计算与 matplotlib 渲染组件

TrajectoryCalculator: 根据 GunCoefficients 与配件组合计算累积偏移序列
TrajectoryView: 嵌入到 PySide6 的 matplotlib 画布

@author huquanzhi
@since 2026-06-18 19:40
@version 1.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import matplotlib

matplotlib.use("QtAgg")  # 必须在导入 pyplot 之前

from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget  # noqa: E402

from ..ballistic_data import AttachmentCategory, AttachmentItem, GunCoefficients


# ---------------------------------------------------------------------------
# 中文字体设置
# ---------------------------------------------------------------------------

# Windows 常见中文字体（按优先级匹配）
_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",   # 微软雅黑
    "Microsoft YaHei UI",
    "SimHei",            # 黑体
    "SimSun",            # 宋体
    "Microsoft JhengHei",# 微软正黑（繁体）
    "PingFang SC",       # macOS
    "Noto Sans CJK SC",  # Linux
    "WenQuanYi Zen Hei", # Linux
    "Arial Unicode MS",
]


def _configure_cjk_font() -> str:
    """找到第一个可用的 CJK 字体并设置为 matplotlib 默认字体"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in _CJK_FONT_CANDIDATES:
        if candidate in available:
            matplotlib.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["axes.unicode_minus"] = False
            return candidate
    # 兜底：保留默认
    matplotlib.rcParams["axes.unicode_minus"] = False
    return ""


# 模块加载时立即配置
_CJK_FONT = _configure_cjk_font()


# ---------------------------------------------------------------------------
# 计算
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryPoint:
    """单发子弹的累积偏移（像素）"""

    dx: float  # 水平偏移（右为正）
    dy: float  # 垂直偏移（下为正）
    shot_index: int  # 第几发


class TrajectoryCalculator:
    """根据系数生成 30 发弹道轨迹

    模型:
      - 每发子弹的瞬时偏移 = (coef * 缩放) * 方向向量
      - 累积偏移即鼠标补偿位置
      - 系数越大 → 压枪幅度越大
      - 配件 ratio < 1 → 后坐力小 → 压枪少
      - 配件 ratio = 1 → 裸配
    """

    # 单发基础垂直/水平像素偏移（与 lua MoveMouseRelative 一致量级）
    BASE_VERTICAL = 4.0
    BASE_HORIZONTAL = 0.6

    # 衰减曲线：前几发大，后几发小（模拟真实后坐力）
    DECAY = 0.92

    # 随机扰动幅度（水平方向模拟横向抖动）
    JITTER = 0.3

    DEFAULT_SHOTS = 30

    @classmethod
    def calculate(
        cls,
        gun: GunCoefficients,
        scope_factor: float = 1.0,
        crouch: bool = False,
        prone: bool = False,
        shots: int = DEFAULT_SHOTS,
        attachment_multiplier: float = 1.0,
    ) -> list[TrajectoryPoint]:
        """生成单条轨迹

        Args:
            gun: 枪械系数
            scope_factor: 倍镜系数（1/2/3 倍）
            crouch: 是否下蹲
            prone: 是否趴姿
            shots: 子弹数量
            attachment_multiplier: 配件综合系数（满配 0.7~0.9，裸配 1.0）
        """
        if gun.mode == 0:
            # 禁用模式返回空
            return []

        # 基础系数：自身系数 * 配件系数
        if prone:
            base_coef = gun.prone
        elif crouch:
            base_coef = gun.crouch
        else:
            base_coef = gun.coef

        # 配件综合系数作用于「裸配」系数
        effective_coef = base_coef * attachment_multiplier * scope_factor
        # 缩放：把系数转换为像素偏移量
        # lua 中 coef 是 0.x~10+ 的大数值，物理位移约 2~6 像素
        scale = cls.BASE_VERTICAL / 5.0  # 让 coef=5 时偏移 = 4 像素

        points: list[TrajectoryPoint] = []
        cum_dx = 0.0
        cum_dy = 0.0
        decay = 1.0

        for i in range(shots):
            # 衰减（首发最强）
            decay = cls.DECAY**i
            # 第 i 发的瞬时垂直偏移（向下）
            dy = cls.BASE_VERTICAL * effective_coef * scale * decay
            # 水平偏移：sin 模拟左右抖动
            dx = cls.BASE_HORIZONTAL * math.sin(i * 0.7) * decay

            cum_dx += dx
            cum_dy += dy
            points.append(TrajectoryPoint(dx=cum_dx, dy=cum_dy, shot_index=i + 1))

        return points

    @classmethod
    def combined_coef(
        cls,
        gun: GunCoefficients,
        muzzle: AttachmentItem | None,
        grip: AttachmentItem | None,
        stock: AttachmentItem | None,
    ) -> float:
        """计算「满配综合系数」= 自身系数 × 三个配件 ratio

        注: lua 实际公式是 coef × muzzle.ratio × grip.ratio × stock.ratio
        """
        m = muzzle.ratio if muzzle else 1.0
        g = grip.ratio if grip else 1.0
        s = stock.ratio if stock else 1.0
        return gun.coef * m * g * s


# ---------------------------------------------------------------------------
# 视图
# ---------------------------------------------------------------------------


class TrajectoryView(QWidget):
    """弹道轨迹预览图

    嵌入 matplotlib FigureCanvasQTAgg 到 PySide6 窗口。
    显示两条轨迹：裸配（红）vs 当前配件（绿）。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gun: GunCoefficients | None = None
        self._muzzle: AttachmentItem | None = None
        self._grip: AttachmentItem | None = None
        self._stock: AttachmentItem | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(5, 5), dpi=100, facecolor="#1e1e1e")
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas)

        self._ax = self._figure.add_subplot(111)
        self._configure_axes()
        self._canvas.draw_idle()

    def _configure_axes(self) -> None:
        ax = self._ax
        ax.set_facecolor("#1e1e1e")
        ax.set_title("弹道轨迹预览", color="white", fontsize=12, fontweight="bold")
        ax.set_xlabel("水平偏移 (像素)", color="white", fontsize=9)
        ax.set_ylabel("垂直偏移 (像素，向下)", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#666")
        ax.grid(True, color="#444", linestyle="--", linewidth=0.5, alpha=0.7)
        ax.axhline(y=0, color="#888", linewidth=0.5)
        ax.axvline(x=0, color="#888", linewidth=0.5)

    def update_view(
        self,
        gun: GunCoefficients | None,
        muzzle: AttachmentItem | None = None,
        grip: AttachmentItem | None = None,
        stock: AttachmentItem | None = None,
    ) -> None:
        """刷新视图

        Args:
            gun: 当前选中枪支；None 时显示空图
            muzzle/grip/stock: 当前选中的配件；None 时按「裸配」处理
        """
        self._gun = gun
        self._muzzle = muzzle
        self._grip = grip
        self._stock = stock
        self._redraw()

    def _redraw(self) -> None:
        self._ax.clear()
        self._configure_axes()

        if self._gun is None or self._gun.mode == 0:
            self._ax.text(
                0.5, 0.5,
                "未选中枪械 / 模式=0 禁用",
                transform=self._ax.transAxes,
                ha="center", va="center",
                color="#888", fontsize=12,
            )
            self._canvas.draw_idle()
            return

        # 当前配件轨迹（绿）
        cur_points = TrajectoryCalculator.calculate(
            self._gun,
            attachment_multiplier=self._current_attachment_multiplier(),
        )
        if cur_points:
            xs = [p.dx for p in cur_points]
            ys = [p.dy for p in cur_points]
            self._ax.plot(
                xs, ys,
                color="#4caf50", linewidth=1.5, alpha=0.9,
                marker="o", markersize=3, label="当前配置",
            )
            # 标注首末发
            self._ax.annotate(
                f"首发\n({xs[0]:.1f}, {ys[0]:.1f})",
                xy=(xs[0], ys[0]), xytext=(8, 8),
                textcoords="offset points",
                color="#4caf50", fontsize=7,
            )
            self._ax.annotate(
                f"末发\n({xs[-1]:.1f}, {ys[-1]:.1f})",
                xy=(xs[-1], ys[-1]), xytext=(8, -12),
                textcoords="offset points",
                color="#4caf50", fontsize=7,
            )

        # 裸配轨迹（红，对比）
        bare_points = TrajectoryCalculator.calculate(
            self._gun, attachment_multiplier=1.0,
        )
        if bare_points:
            xs = [p.dx for p in bare_points]
            ys = [p.dy for p in bare_points]
            self._ax.plot(
                xs, ys,
                color="#f44336", linewidth=1.0, alpha=0.6,
                marker="x", markersize=3, label="裸配（对比）",
            )

        self._ax.legend(loc="upper right", fontsize=8, facecolor="#1e1e1e", edgecolor="#666", labelcolor="white")
        self._ax.set_title(
            f"弹道轨迹 - {self._gun.name}", color="white", fontsize=12, fontweight="bold"
        )
        # 等比例
        self._ax.set_aspect("equal", adjustable="datalim")
        self._figure.tight_layout()
        self._canvas.draw_idle()

    def _current_attachment_multiplier(self) -> float:
        """计算当前配件组合的综合系数

        公式: muzzle.ratio * grip.ratio * stock.ratio
        若某项为 None 则视为 1.0
        """
        m = self._muzzle.ratio if self._muzzle else 1.0
        g = self._grip.ratio if self._grip else 1.0
        s = self._stock.ratio if self._stock else 1.0
        return m * g * s
