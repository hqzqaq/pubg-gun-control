# PUBG Gun Control

一款配合罗技G HUB压枪宏在PUBG游戏中使用的枪械切换显示工具。通过监听鼠标和键盘组合键，在屏幕左上角显示当前选中的枪械名称。

[English Version](README-EN.md)

## 功能特性

- 屏幕左上角浮窗显示枪械名称（白底红字，置顶显示）
- 浮窗鼠标穿透，不干扰游戏操作
- 支持多种枪械切换组合
- 大写锁定键控制压枪模式开关
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
| LShift + 鼠标前进侧键 | SCAR-L |
| LShift + 鼠标后退侧键 | AUG    |

### 压枪模式控制

| 操作                 | 功能                  |
| ------------------ | ------------------- |
| 按下大写锁定键（当前显示"无"）   | 开启压枪模式，显示默认枪械（UMP5） |
| 按下大写锁定键（当前为枪械名称）   | 关闭压枪模式，显示"无"        |
| 按下 G / 3 / 4 / 5 键 | 取消压枪模式，显示"无"        |
| 按下 Tab 键           | 取消压枪模式，显示"无"        |
| 大写锁定关闭             | 显示"无"               |

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
["lshift + G5"] = "SCAR-L" -- 左Shift + 鼠标侧键前进 = SCAR-L压枪
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
│   ├── input_listener.py   # 热键监听模块
│   ├── overlay_window.py   # 浮窗显示模块
│   └── tray_icon.py        # 系统托盘模块
├── main.py                 # 主程序入口
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

如需修改默认压枪枪械，编辑 `src/pubg_gun_control/input_listener.py`：

```python
class InputListener:
    # 默认压枪枪械
    DEFAULT_GUN = "UMP5"  # 修改这里可以更改默认枪械
```

需要同步修改 `1.2.2-2024.5.20.-GHUB.-github.lua` 中的 `G_bind` 配置。

## 更新日志

### v1.0.6 (2026-04-06)
- 修复：浮窗窗口现在支持鼠标穿透，不再干扰游戏操作
- 优化：浮窗仅作为展示使用，键盘和鼠标事件会穿透到下方窗口

## 免责说明

本工具仅供学习交流使用，请遵守游戏用户协议和相关法律法规。
