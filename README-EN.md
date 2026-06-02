# PUBG Gun Control

A weapon switch display tool for PUBG, designed to work with Logitech G HUB recoil macros. It monitors mouse and keyboard combinations to display the currently selected weapon name in the upper-left corner of the screen.

[中文版](README.md)

## Features

- Floating window display in upper-left corner (white background, red text, always on top)
- Mouse click-through overlay, no interference with game operations
- Multiple weapon switch combinations
- Caps Lock key controls recoil mode on/off
- **Weapon Lock Feature**: Ctrl + Alt toggles lock/unlock weapon switching, overlay turns yellow when locked
- **Visual Shortcut Configuration**: Open settings window via system tray menu to modify shortcut display text
- **Config File Support**: Shortcuts saved in config.json with persistent storage
- Works with Logitech G HUB recoil macros
- `1.2.2-2024.5.20.-GHUB.-github.lua` is the recoil script, needs to be imported into G HUB, tutorials available on Bilibili etc.
- `Mouse shortcuts are consistent with the recoil script. If you need to change shortcuts, weapon configurations, or recoil trajectory parameters, you can modify them yourself, AI can help with modifications`
- The recoil trajectory parameters in `1.2.2-2024.5.20.-GHUB.-github.lua` may `need to be adjusted according to your own mouse sensitivity`

## Screenshots

### G HUB Interface

!\[GHUB Interface]\(images/GHUB.png null)

### Script Interface

!\[Script Interface]\(images/脚本.png null)

<br />

pubg game

!\[pubg game]\(images/游戏内界面.png null)

## Important Notes

**⚠️ IMPORTANT: The program must be started as Administrator, otherwise it will not work in the game!**

This is because the game runs at a higher privilege level, and input monitoring at normal privilege cannot take effect in the game process.

### How to Start

1. **Right-click to run as Administrator**: Right-click `PUBG-Gun-Control.exe` → Select "Run as administrator"
2. **Create a shortcut**: Right-click → Properties → Shortcut → Advanced → Check "Run as administrator"

## Key Bindings

### Weapon Switch Combinations (When Caps Lock is ON)

| Combination                   | Weapon |
| ----------------------------- | ------ |
| LAlt + Mouse Forward Button   | MP5k   |
| LAlt + Mouse Back Button      | UMP5   |
| LCtrl + Mouse Forward Button  | M416   |
| LCtrl + Mouse Back Button     | ACE32  |
| LShift + Mouse Forward Button | Beryl M762 |
| LShift + Mouse Back Button    | AUG    |

### Recoil Mode Control

| Action                                          | Function                                       |
| ----------------------------------------------- | ---------------------------------------------- |
| Press Caps Lock (currently showing "None")      | Enable recoil mode, show default weapon (UMP5) |
| Press Caps Lock (currently showing weapon name) | Disable recoil mode, show "None"               |
| Press G / 3 / 4 / 5 keys                        | Cancel recoil mode, show "None"                |
| Press Tab key                                   | Cancel recoil mode, show "None"                |
| Caps Lock OFF                                   | Show "None"                                    |
| Press Ctrl + Alt                                | Lock/Unlock weapon switching (overlay turns yellow when locked) |

## Using with Logitech G HUB

### G HUB Macro Script Description

This project uses the `1.2.2-2024.5.20.-GHUB.-github.lua` macro script, which is an open source PUBG recoil macro.

### Macro Script Weapon Configuration

The `G_bind` configuration in the lua script has the following mappings:

```lua
-- LAlt + G key weapon switch
["lalt + G4"] = "UMP45"   -- Left Alt + Mouse back button = UMP5 recoil
["lalt + G5"] = "MP5K"    -- Left Alt + Mouse forward button = MP5K recoil

-- LCtrl + G key weapon switch
["lctrl + G4"] = "ACE32"  -- Left Ctrl + Mouse back button = ACE32 recoil
["lctrl + G5"] = "M416"   -- Left Ctrl + Mouse forward button = M416 recoil

-- LShift + G key weapon switch
["lshift + G4"] = "AUG"    -- Left Shift + Mouse back button = AUG recoil
["lshift + G5"] = "Beryl M762" -- Left Shift + Mouse forward button = Beryl M762 recoil
```

### G HUB Setup Instructions

1. Open G HUB software
2. Select your mouse device
3. Click "+" to add a command
4. Select "Script" type
5. Paste the lua script content
6. Bind mouse **Forward button** to **G4**
7. Bind mouse **Back button** to **G5**

### Recommended Sensitivity Settings

Recommended PUBG in-game sensitivity settings from the lua script:

```
ADS Sensitivity: 70
Hip Fire Sensitivity (Aim): 0.55
2x Scope: 1.4
3x Scope: 3.6
4x Scope: 3.0
6x Scope: 1.25
DPI: 1400
Resolution: 1080P
```

## Project Structure

```
pubg-gun-control/
├── src/pubg_gun_control/
│   ├── __init__.py
│   ├── config_manager.py   # Configuration manager module
│   ├── input_listener.py   # Input listener module
│   ├── overlay_window.py   # Overlay window module
│   ├── settings_window.py  # Settings window module
│   └── tray_icon.py        # System tray module
├── main.py                 # Main program entry
├── config.json             # Shortcut configuration file
├── pubg_gun_control.spec   # PyInstaller build config
└── pyproject.toml          # Project config
```

## Development

### Requirements

- Python 3.12+
- uv package manager

### Install Dependencies

```bash
cd pubg-gun-control
uv sync
```

### Run Program

```bash
uv run python main.py
```

### Build as exe

```bash
uv run pyinstaller pubg_gun_control.spec --clean
```

Built files are located in `dist/PUBG-Gun-Control/` directory.

## GitHub Actions Auto Build

Pushing `v*` tags will automatically trigger build and create Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Configuration

### Shortcut Configuration

Shortcut configurations are saved in the `config.json` file with the following format:

```json
{
  "shortcuts": [
    {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"},
    {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
    {"modifier": "ctrl", "mouse_button": "forward", "text": "M416"},
    {"modifier": "ctrl", "mouse_button": "backward", "text": "ACE32"},
    {"modifier": "shift", "mouse_button": "forward", "text": "Beryl M762"},
    {"modifier": "shift", "mouse_button": "backward", "text": "AUG"}
  ]
}
```

You can open the visual configuration window via the "Settings" option in the system tray menu, and modifications will be saved automatically.

### Default Weapon Configuration

To change the default recoil weapon, edit `src/pubg_gun_control/config_manager.py`:

```python
def get_default_config() -> list[dict[str, str]]:
    return [
        {"modifier": "alt", "mouse_button": "forward", "text": "MP5k"},
        # ... Change the text of the first item to modify the default weapon
    ]
```

You also need to sync modify the `G_bind` configuration in `1.2.2-2024.5.20.-GHUB.-github.lua`.

## Changelog

### v1.0.9 (2026-06-02)
- **Optimize**: Optimized code structure and performance
- **Fix**: Fixed known issues

### v1.0.8 (2026-05-01)
- **Fix**: Fixed Caps Lock toggle delay issue (5-second delay), now responds instantly
- **Fix**: Fixed config file not saving after PyInstaller packaging
- **Fix**: Fixed potential crash caused by tkinter cross-thread operations
- **Refactor**: Extracted `ShortcutMatcher` class to separate input listener responsibilities
- **Refactor**: Implemented thread-safe UI updates using `queue.Queue`
- **Optimize**: Added complete type annotations for better code maintainability
- **Optimize**: Replaced `print` statements with `logging` module
- **Optimize**: Extracted hardcoded values in `OverlayWindow` to module constants

### v1.0.7 (2026-04-19)
- Feature: Weapon lock functionality, Ctrl + Alt toggles lock/unlock weapon switching
- Feature: Visual shortcut configuration via system tray settings window
- Feature: Config file support, shortcuts saved in config.json
- Optimize: Overlay visual feedback for locked state (yellow background, dark red text)
- Fix: Updated default weapon configuration from SCAR-L to Beryl M762

### v1.0.6 (2026-04-06)
- Fix: Overlay window now supports mouse click-through, no longer interfering with game operations
- Optimize: Overlay only serves as a display, keyboard and mouse events pass through to the window below

## Disclaimer

This tool is for learning and communication purposes only. Please comply with the game's terms of service and relevant laws and regulations.
