# PUBG Gun Control

一款配合罗技G HUB压枪宏在PUBG游戏中使用的枪械切换显示工具。通过监听鼠标和键盘组合键，在屏幕左上角显示当前选中的枪械名称。

[English Version](README-EN.md)

## 功能特性

- 屏幕左上角浮窗显示枪械名称、倍镜、配件信息（白底红字，置顶显示）
- 浮窗鼠标穿透，不干扰游戏操作
- 支持多种枪械切换组合
- 大写锁定键控制压枪模式开关
- **枪械锁定功能**：RCtrl + 鼠标G4键 锁定/解锁当前枪械，锁定后浮窗变黄色，无法切换枪械
- **快捷键可视化配置**：通过系统托盘菜单打开设置窗口，修改快捷键显示文本、勾选每把枪支持的配件
- **配置文件支持**：快捷键配置保存在 config.json，支持持久化存储
- **配件循环切换**：鼠标中键 + 修饰键循环切换枪口/握把/枪托
- **倍镜模式切换**：RAlt + 鼠标侧键切换 2/3 倍镜，浮窗左上角显示当前倍镜
- **一键重置**：LCtrl + LAlt + Win 组合键重置所有状态（枪械、倍镜、配件、锁定）
- **弹道系数可视化编辑器**：托盘菜单 → 打开编辑器，可视化调整 lua 脚本中的 8 个枪械系数、模式（禁用/启用/连点）、配件组合，实时预览弹道轨迹
- **倍镜切换预览**：编辑器支持 1x/2x/3x 倍镜切换与多倍镜叠加对比
- **预设管理**：编辑器支持保存/加载/删除配置预设（按 DPI/分辨率/鼠标型号切档）
- **lua 自动备份**：编辑器保存时自动生成 `.bak` 备份
- 配合罗技G HUB压枪宏使用
- 1.2.2-2024.5.20.-GHUB.-github.lua为压枪脚本，需要导入到G HUB中，具体教程可搜b站等
- `鼠标快捷键是和压枪脚本保持一致的，如果需要更换快捷键或者枪械配置、压枪弹道参数等需要自行修改，借助AI修改也比较容易`
- 1.2.2-2024.5.20.-GHUB.-github.lua压枪脚本中的弹道参数可能`需要根据自身的鼠标灵敏度自行调整`

## 配图

### G HUB界面

!\[GHUB界面]\(images/GHUB.png null)

### 脚本界面

!\[脚本界面]\(images/脚本.png null)

<br />

游戏内界面

!\[游戏内界面]\(images/游戏内界面.png null)

## 注意事项

**⚠️ 重要：程序必须以管理员身份启动，否则在游戏中不会生效！**

这是因为游戏运行在较高的权限级别，普通权限的输入监听无法在游戏进程中生效。

### 启动方式

1. **右键使用管理员权限启动**：右键点击 `PUBG-Gun-Control.exe` → 选择"以管理员身份运行"
2. **创建快捷方式**：右键 → 属性 → 快捷方式 → 高级 → 勾选"用管理员身份运行"

## 按键说明

### 枪械切换组合（大写锁定开启时）

| 组合键             | 显示枪械   |
| --------------- | ------ |
| LAlt + 鼠标前进侧键   | MP5k   |
| LAlt + 鼠标后退侧键   | UMP5   |
| LCtrl + 鼠标前进侧键  | M416   |
| LCtrl + 鼠标后退键   | ACE32  |
| LShift + 鼠标前进侧键 | Beryl M762 |
| LShift + 鼠标后退侧键 | AUG    |

### 配件循环切换（大写锁定开启时）

| 组合键              | 功能     |
| ---------------- | ------ |
| LAlt + 鼠标中键(G3)   | 循环切换枪口 |
| LCtrl + 鼠标中键(G3)  | 循环切换握把 |
| LShift + 鼠标中键(G3) | 循环切换枪托 |

配件可选值：
- 枪口：无 / 补偿器 / 消焰器 / 消音器 / 制退器
- 握把：无 / 垂直 / 斜向 / 拇指 / 半截 / 轻型
- 枪托：无 / 战术 / 重型

### 倍镜模式切换（大写锁定开启时）

| 组合键                | 功能   |
| ------------------ | ---- |
| RAlt + 鼠标G5(前进)   | 切换2倍镜 |
| RAlt + 鼠标G4(后退)   | 切换3倍镜 |
| RCtrl + 鼠标G5(前进)  | 切换1倍镜 |

切换后浮窗左上角会显示当前倍镜（1/2/3）。

### 压枪模式控制

| 操作                 | 功能                  |
| ------------------ | ------------------- |
| 按下大写锁定键（当前显示"无"）   | 开启压枪模式，显示默认枪械（UMP5） |
| 按下大写锁定键（当前为枪械名称）   | 关闭压枪模式，显示"无"        |
| 按下 1 键              | 开启压枪模式（等同 Caps Lock 当前显示"无"时） |
| 按下 2 键              | 取消压枪模式，显示"无"        |
| 按下 G / 3 / 4 / 5 键 | 取消压枪模式，显示"无"        |
| 按下 Tab 键           | 取消压枪模式，显示"无"        |
| 大写锁定关闭             | 显示"无"               |
| RCtrl + 鼠标G4(后退)  | 锁定/解锁枪械切换（锁定后浮窗变黄色，无法切换） |
| LCtrl + LAlt + Win  | 一键重置所有状态（枪械、倍镜、配件、锁定） |

## 配合罗技G HUB使用

### G HUB宏脚本说明

本项目配合使用 `1.2.2-2024.5.20.-GHUB.-github.lua` 宏脚本，该脚本是开源的PUBG压枪宏。

### 宏脚本的枪械配置

lua脚本中的 `G_bind` 配置了以下映射关系：

```lua
-- LAlt + G键 切换枪械
["lalt + G4"] = "UMP45"   -- 左Alt + 鼠标侧键后退 = UMP5压枪
["lalt + G5"] = "MP5K"    -- 左Alt + 鼠标侧键前进 = MP5K压枪

-- LCtrl + G键 切换枪械
["lctrl + G4"] = "ACE32"  -- 左Ctrl + 鼠标侧键后退 = ACE32压枪
["lctrl + G5"] = "M416"   -- 左Ctrl + 鼠标侧键前进 = M416压枪

-- LShift + G键 切换枪械
["lshift + G4"] = "AUG"    -- 左Shift + 鼠标侧键后退 = AUG压枪
["lshift + G5"] = "Beryl M762" -- 左Shift + 鼠标侧键前进 = Beryl M762压枪
```

### G HUB设置方法

1. 打开G HUB软件
2. 选择你的鼠标设备
3. 点击"+"添加命令
4. 选择"脚本"类型
5. 将lua脚本内容粘贴进去
6. 将鼠标的**前进侧键**绑定为 **G4**
7. 将鼠标的**后退侧键**绑定为 **G5**

### 灵敏度推荐配置

lua脚本中推荐的PUBG游戏内灵敏度设置：

```
开镜灵敏度(ADS): 70
腰射灵敏度(Aim): 0.55
2倍镜: 1.4
3倍镜: 3.6
4倍镜: 3.0
6倍镜: 1.25
DPI: 1400
分辨率: 1080P
```

## 项目结构

```
pubg-gun-control/
├── src/pubg_gun_control/
│   ├── __init__.py
│   ├── config_manager.py   # 配置管理模块
│   ├── input_listener.py   # 热键监听模块
│   ├── overlay_window.py   # 浮窗显示模块
│   ├── settings_window.py  # 设置窗口模块
│   └── tray_icon.py        # 系统托盘模块
├── main.py                 # 主程序入口
├── config.json             # 快捷键配置文件
├── pubg_gun_control.spec   # PyInstaller打包配置
└── pyproject.toml          # 项目配置
```

## 开发

### 环境要求

- Python 3.12+
- uv 包管理器

### 安装依赖

```bash
cd pubg-gun-control
uv sync
```

### 运行程序

```bash
uv run python main.py
```

### 打包为exe

```bash
uv run pyinstaller pubg_gun_control.spec --clean
```

打包后的文件位于 `dist/PUBG-Gun-Control/` 目录。

## GitHub Actions 自动构建

推送 `v*` 标签会自动触发构建并创建Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 配置文件说明

### 快捷键配置

快捷键配置保存在 `config.json` 文件中，格式如下：

```json
{
  "shortcuts": [
    {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"},
    {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
    {"modifier": "ctrl", "mouse_button": "forward", "text": "M416"},
    {"modifier": "ctrl", "mouse_button": "backward", "text": "ACE32"},
    {"modifier": "shift", "mouse_button": "forward", "text": "Beryl M762"},
    {"modifier": "shift", "mouse_button": "backward", "text": "AUG"}
  ],
  "attachments": [
    {"modifier": "alt", "mouse_button": "middle", "category": "muzzle", "label": "枪口"},
    {"modifier": "ctrl", "mouse_button": "middle", "category": "grip", "label": "握把"},
    {"modifier": "shift", "mouse_button": "middle", "category": "stock", "label": "枪托"}
  ],
  "gun_attachments": {
    "UMP5":       {"muzzle": true, "grip": true, "stock": false},
    "MP5k":       {"muzzle": true, "grip": true, "stock": true},
    "M416":       {"muzzle": true, "grip": true, "stock": true},
    "ACE32":      {"muzzle": true, "grip": true, "stock": true},
    "Beryl M762": {"muzzle": true, "grip": true, "stock": false},
    "AUG":        {"muzzle": true, "grip": true, "stock": false}
  }
}
```

可以通过系统托盘菜单的"设置"选项打开可视化配置窗口，修改后自动保存。
设置窗口支持修改枪械显示文本，并通过勾选配置每把枪是否支持 枪口/握把/枪托 三类配件。

### 默认枪械配置

如需修改默认压枪枪械，编辑 `src/pubg_gun_control/config_manager.py`：

```python
def get_default_config() -> list[dict[str, str]]:
    return [
        {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
        # 修改第一项的 text 即可更改默认枪械
    ]
```

需要同步修改 `1.2.2-2024.5.20.-GHUB.-github.lua` 中的 `G_bind` 配置。

## 更新日志

### v1.1.1 (2026-06-18)
- **新增**：弹道系数可视化编辑器，托盘菜单「打开编辑器」或独立运行 `main_editor.py` 启动
- **新增**：8 个枪械系数（自身/下蹲/屏息/裸配/满配/趴姿/2 倍镜/3 倍镜）可视化调整
- **新增**：模式切换（0 禁用 / 1 启用 / 2 连点）下拉选择
- **新增**：配件下拉选择（5 枪口 × 6 握把 × 3 枪托）+ 满配综合系数自动计算
- **新增**：matplotlib 弹道轨迹预览，实时显示调参效果
- **新增**：1x/2x/3x 倍镜切换与多倍镜叠加对比
- **新增**：预设管理（保存/加载/删除），按 DPI / 分辨率 / 鼠标型号切档
- **新增**：lua 文件自动备份（保存时生成 `<原文件>.bak`）
- **新增**：最近文件列表（5 个），托盘菜单快捷访问
- **依赖**：引入 PySide6 + matplotlib

### v1.10 (2026-06-18)
- **新增**：配件循环切换功能，支持 枪口 / 握把 / 枪托 三类配件；通过 LAlt / LCtrl / LShift + 鼠标中键 循环切换
- **新增**：倍镜模式切换功能，RAlt + 鼠标G5/G4 切换 2/3 倍镜，RCtrl + 鼠标G5 切换 1 倍镜；浮窗左上角显示当前倍镜
- **新增**：一键重置功能，LCtrl + LAlt + Win 组合键重置所有状态（枪械、倍镜、配件、锁定）
- **新增**：1/2 数字键控制压枪模式开关（1 开启，2 取消）
- **新增**：设置窗口支持勾选每把枪支持的配件类型，未勾选的配件在切换枪械时自动重置为"无"
- **优化**：浮窗显示内容扩展为 倍镜 + 枪械名称 + 配件信息
- **优化**：锁定快捷键从 Ctrl+Alt 调整为 RCtrl+鼠标G4，避免与压枪组合键冲突
- **重构**：将附件/倍镜/重置等逻辑统一抽离到 `InputListener`，配置数据集中到 `config.json`

### v1.0.9 (2026-06-02)
- **优化**：优化代码结构和性能
- **修复**：修复已知问题

### v1.0.8 (2026-05-01)
- **修复**：修复大写锁定切换延迟问题（5秒延迟），现在切换即时响应
- **修复**：修复 PyInstaller 打包后配置文件无法保存的问题
- **修复**：修复 tkinter 跨线程操作导致的潜在崩溃问题
- **重构**：提取 `ShortcutMatcher` 类，拆分输入监听器的职责
- **重构**：使用 `queue.Queue` 实现线程安全的 UI 更新
- **优化**：补全所有类型注解，提升代码可维护性
- **优化**：使用 `logging` 模块替代 `print` 输出
- **优化**：提取 `OverlayWindow` 中的硬编码配置为模块常量

### v1.0.7 (2026-04-19)
- 新增：枪械锁定功能，Ctrl + Alt 组合键锁定/解锁枪械切换
- 新增：快捷键可视化配置，通过系统托盘菜单打开设置窗口修改
- 新增：配置文件支持，快捷键配置保存在 config.json
- 优化：浮窗锁定状态视觉反馈（黄色背景，深红色文字）
- 修复：更新默认枪械配置从 SCAR-L 改为 Beryl M762

### v1.0.6 (2026-04-06)
- 修复：浮窗窗口现在支持鼠标穿透，不再干扰游戏操作
- 优化：浮窗仅作为展示使用，键盘和鼠标事件会穿透到下方窗口

## 免责说明

本工具仅供学习交流使用，请遵守游戏用户协议和相关法律法规。
