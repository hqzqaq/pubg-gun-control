# 弹道系数可视化编辑器 Spec

## Why
当前用户调节 GHUB lua 脚本里的枪械系数（`canUse` 表）需要手动编辑源码：找到对应行、改数字、保存、重载 GHUB、进游戏测试。**全程没有图形化预览**，调参纯靠"猜+试"。需要一款桌面端 GUI 工具，把这一流程从盲调升级为所见即所得，并支持配件组合实时算综合系数、预设保存/加载、防误操作。

## What Changes
- 新增 Python 桌面 GUI 编辑器（独立可执行入口 `main_editor.py`），独立于游戏浮窗运行
- 新增 lua 文件解析器/序列化器（`lua_parser.py`），支持读写 `1.2.2-2024.5.20.-GHUB.-github.lua` 的 `canUse` 与 `attachmentConfig` 表
- 新增数据模型层（`ballistic_data.py`）：枪械、配件、配置预设的 dataclass
- 新增图形界面（`editor_ui/` 子包）：枪械列表、明细面板、配件面板、弹道预览图
- 新增预设管理（`presets/` 目录）：按 DPI / 分辨率 / 鼠标型号保存多套配置
- 在 `pyproject.toml` 中新增依赖：PySide6、matplotlib
- 在 `main.py` 托盘菜单中新增「打开编辑器」入口

## Impact
- 新增 spec：本次新增（无既有 spec 关联）
- 新增代码：
  - `src/pubg_gun_control/lua_parser.py`
  - `src/pubg_gun_control/ballistic_data.py`
  - `src/pubg_gun_control/editor_ui/__init__.py`
  - `src/pubg_gun_control/editor_ui/main_window.py`
  - `src/pubg_gun_control/editor_ui/gun_list_panel.py`
  - `src/pubg_gun_control/editor_ui/gun_detail_panel.py`
  - `src/pubg_gun_control/editor_ui/attachment_panel.py`
  - `src/pubg_gun_control/editor_ui/trajectory_view.py`
  - `src/pubg_gun_control/editor_ui/preset_dialog.py`
- 修改代码：
  - `pyproject.toml`：新增依赖
  - `main.py`：托盘菜单增加入口
  - `src/pubg_gun_control/tray_icon.py`：增加菜单项回调
- **BREAKING**：无（编辑器是独立工具，不影响现有 overlay / input_listener 行为）

## ADDED Requirements

### Requirement: 解析 lua 弹道系数表
系统 SHALL 提供 `LuaBallisticParser`，能解析 `1.2.2-2024.5.20.-GHUB.-github.lua` 中的：
- `canUse` 表：按弹药类型分组的枪械列表（每把枪含 name、mode、8 个系数）
- `attachmentConfig` 表：muzzle/grip/stock 三类配件的 name/label/ratio

#### Scenario: 解析成功
- **WHEN** 传入合法 lua 文件路径
- **THEN** 返回 `BallisticConfig` 对象，包含全部枪械与配件
- **AND** 数字精度保留到小数点后 2 位（与 lua 原文件格式一致）

#### Scenario: 解析失败容错
- **WHEN** lua 文件不存在或格式异常
- **THEN** 抛出 `BallisticParseError`，附带行号与上下文片段
- **AND** 编辑器界面显示「打开失败」对话框，不崩溃

### Requirement: 序列化回写 lua
系统 SHALL 提供 `LuaBallisticParser.serialize(config) -> str`，能将编辑后的配置写回 lua 文本。

#### Scenario: 保持格式
- **WHEN** 序列化时
- **THEN** 输出文本缩进、注释、对齐与原文件一致（用制表符缩进，列宽对齐到与原表相同）
- **AND** 数字格式与原文件一致（如 `1.95` 而非 `1.950000`）

#### Scenario: 写前备份
- **WHEN** 用户点击「保存到 lua」
- **THEN** 自动备份原文件为 `*.lua.bak`（覆盖前一份备份）
- **AND** 写入新内容到原路径
- **AND** 弹窗提示「保存成功」，并显示备份文件路径

### Requirement: 弹道系数数据模型
系统 SHALL 提供 dataclass 描述枪械与配件：
- `GunCoefficients`：name、mode、(coef, crouch, breath, bare, full, prone, scope2x, scope3x) 8 个系数
- `AttachmentItem`：name、label、ratio
- `AttachmentCategory`：muzzle / grip / stock，每类含一组 `AttachmentItem`
- `BallisticConfig`：ammo_groups (dict[str, list[GunCoefficients]])、attachment_config (dict[str, AttachmentCategory])

### Requirement: 编辑器主窗口
系统 SHALL 提供 `BallisticEditorWindow`（基于 PySide6），窗口分三栏：
- 左侧：枪械列表（按弹药类型分组，TreeView 展示，模式 0/1/2 用不同图标）
- 中部：当前选中枪的 8 个系数编辑（QDoubleSpinBox，步长 0.01）
- 右侧：弹道预览图（matplotlib embedded，叠加显示当前系数下的预期补偿轨迹）

#### Scenario: 选中枪支联动
- **WHEN** 用户点击左侧列表的某把枪
- **THEN** 中部面板填充该枪的 8 个系数
- **AND** 右侧弹道图重新渲染

#### Scenario: 修改系数实时预览
- **WHEN** 用户在中部修改任一系数
- **THEN** 右侧弹道图立即重绘
- **AND** 状态栏显示「未保存」标记

#### Scenario: 模式切换
- **WHEN** 用户在中部修改 `mode` 字段
- **THEN** 左侧列表项的图标立即更新（0=禁用/灰、1=启用/绿、2=连点/蓝）

### Requirement: 配件面板
系统 SHALL 在枪械明细面板下方提供「当前配件组合」选择器：
- 三个 Combobox：枪口 / 握把 / 枪托
- 选中后实时计算「满配综合系数」= 自身系数 × muzzle.ratio × grip.ratio × stock.ratio
- 综合系数显示在面板顶部，2 位小数

#### Scenario: 配件不可用提示
- **WHEN** 当前枪械不支持某配件槽（参考 `gunNoStock`）
- **THEN** 该 Combobox 禁用并显示「不支持」

### Requirement: 弹道轨迹预览
系统 SHALL 使用 matplotlib 绘制弹道轨迹：
- X 轴 = 水平方向像素偏移
- Y 轴 = 垂直方向像素偏移（向下为正）
- 绘制 N 发子弹的累积偏移点（默认 30 发）
- 支持叠加显示：裸配 / 满配 两条轨迹对比

#### Scenario: 渲染 30 发轨迹
- **WHEN** 用户选中一把枪
- **THEN** 图表显示 30 个散点，曲线连接形成轨迹
- **AND** 红色散点=裸配、绿色散点=满配

### Requirement: 预设管理
系统 SHALL 支持把当前配置保存为命名预设（JSON 文件到 `presets/` 目录），并能加载/删除预设。

#### Scenario: 保存预设
- **WHEN** 用户点击「保存预设」并输入名称（如 `M762_1400dpi_1080p`）
- **THEN** 当前 `BallisticConfig` 序列化为 `presets/<name>.json`
- **AND** 弹窗提示成功

#### Scenario: 加载预设
- **WHEN** 用户从预设下拉框选择一项
- **THEN** 主窗口所有面板填充该预设的数值
- **AND** 状态栏显示「已加载预设: <name>」

#### Scenario: 删除预设
- **WHEN** 用户点击「删除预设」并确认
- **THEN** 删除对应 JSON 文件
- **AND** 预设下拉框刷新

### Requirement: 编辑器独立入口
系统 SHALL 提供 `main_editor.py`（位于项目根），能直接启动编辑器：
- `uv run python main_editor.py`
- 启动时弹出文件选择对话框，让用户选择 lua 文件
- 提供「最近打开」记录（保存在 `config.json` 的 `editor` 字段）

### Requirement: 与主应用集成
系统 SHALL 在 `GunControlApp` 的托盘菜单中增加「打开编辑器」入口。

#### Scenario: 托盘菜单调用
- **WHEN** 用户右键托盘图标 → 选中「打开编辑器」
- **THEN** 启动 `BallisticEditorWindow`（独立进程或同进程子窗口）
- **AND** 不阻塞主浮窗的运行

## MODIFIED Requirements

### Requirement: pyproject.toml 依赖
- **MODIFIED**：增加 `PySide6>=6.6.0` 与 `matplotlib>=3.8.0` 到 `[project] dependencies`

### Requirement: config.json 结构
- **MODIFIED**：增加可选字段 `editor.recent_files` (list[str])，保存最近打开的 lua 文件路径，最多 5 个

## REMOVED Requirements
无（本次纯增量，不删除任何已有功能）

## Out of Scope
- 修改 lua 脚本中除 `canUse` / `attachmentConfig` 以外的任何部分
- 直接从 GHUB 进程拉取当前生效的系数（lua 端无 IPC）
- 弹道序列数组（per-shot dx/dy）的可视化（该数据在 lua 脚本的其他位置，超出本次 MVP）
- 在游戏内运行时联动编辑（编辑器设计为离线工具）
- 跨平台支持（仅 Windows 11）
