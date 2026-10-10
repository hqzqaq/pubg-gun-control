# PUBG Gun Control

A weapon switch display and auto-recognition tool for PUBG, designed to work with Logitech G HUB recoil macros. It monitors mouse and keyboard combinations to display the currently selected weapon name, scope and attachments in the upper-left corner of the screen; and it can screenshot-auto-detect the current weapon and attachments, writing the result into `rec.lua` for the GHUB script so recoil parameters switch automatically.

It also provides **stance detection** (auto-switching stand/crouch/prone coefficients), **closed-loop ballistic auto-calibration** (algorithmically deriving the compensation table after live fire) and an **on-screen center crosshair**.

[中文版](README.md)

## Features

### Display & Switching
- Floating window in upper-left corner shows weapon name, scope mode and attachments (white background, red text, always on top)
- Mouse click-through overlay, no interference with game operations
- Overlay position can be unlocked and dragged; coordinates persist across restarts
- Multiple weapon switch combinations
- Caps Lock key controls recoil mode on/off
- **Weapon Lock Feature**: RCtrl + Mouse G4 toggles lock/unlock weapon switching, overlay turns yellow when locked
- **Visual Shortcut Configuration**: Open settings window via system tray menu to modify shortcut display text and per-weapon attachment support
- **Config File Support**: Shortcuts saved in config.json with persistent storage
- **Attachment Cycling**: Modifier key + mouse middle button cycles through muzzle/grip/stock attachments
- **Scope Mode Switching**: RAlt + mouse side buttons switch between 2x/3x scope; current scope is shown at the top-left of the overlay
- **One-Key Reset**: LCtrl + LAlt + Win resets all state (weapon, scope, attachments, lock)

### Stance Detection (Stand / Crouch / Prone)
- **Automatic stance tracking**: listens to in-game keypresses to infer the current stance and writes it to `rec_stance` in `rec.lua`, so the GHUB script switches recoil coefficients accordingly
- Defaults: **C = crouch**, **Z = prone**, **Space = break key** (jumping/vaulting forces a reset to stand); all keys are remappable in settings
- **Break mechanism**: press/release pairing eliminates Windows key auto-repeat, so holding C only toggles once
- **Focus filtering**: stance is only updated while PUBG is in the foreground, avoiding accidental triggers while typing on the desktop
- **Manual correction**: tray menu → "Reset Stance to Stand" for drift caused by being knocked down, entering vehicles, swimming, etc.
- **Base stance conversion**: the ballistic table base can be `stand` or `crouch`; with `crouch` base, standing compensation = 1 / crouch coefficient (the editor shows the live conversion)

### Closed-Loop Ballistic Auto-Calibration
- **Fully automatic**: launched from Editor → "Tools → Closed-Loop Recoil Calibration…", no manual bullet-hole tracing
- **Iterative learning control (ILC)**: round 0 fires uncompensated to measure the raw recoil curve → each later round fires with the current compensation table and measures residual drift → converges in 2~3 rounds
- **Screen-pixel tracking**: uses mss high-frequency screen capture plus OpenCV template matching to track world-reference drift relative to screen center, then splits the curve into per-shot increments by fire rate
- **Automatic Lua conversion**: `V(k) = P*(k) / ((ADS/100) × gun coefficient)`; scope and stance differences are handled by the Lua-side coefficients
- **Non-modal wizard**: runs in a worker thread with live log output; results are applied to the editor's in-memory config (marked dirty) and written back to Lua only through the normal save flow
- Supports ILC (automatic) and manual per-round confirmation modes

### On-Screen Center Crosshair
- Draws a customizable crosshair at screen center, solving the problem of losing aim point when the character is running
- Shapes: cross / dot / circle / cross-dot, with configurable color and size plus live preview
- Two modes: **always on** or **hold a key** (default Shift)
- Multi-monitor aware: the crosshair follows the display under the mouse cursor
- Always-on-top, click-through, tool-window style — never interferes with gameplay

### Auto Recognition
- **Screenshot recognition of current weapon**: press F2 to detect the current weapon, muzzle, grip, stock and scope, then write the result into `rec.lua`
- **dofile mode export**: exports `auto_recognize_ghub.lua` + `auto_recognize_rec.lua`; the GHUB script loads results via `loadstring`, no re-export needed after every edit
- **Dynamic weapon list**: weapon list and weapon-type mapping (AR / SMG) are inferred from the base script's `canUse` groups, so adding a gun requires no manual mapping table
- **ROI selection**: frame the recognition regions on a full-screen capture, with BackSpace to go back to the previous region
- **Guided template capture**: muzzles grouped by weapon type (AR / SMG), scopes cover irons/red dot/holo/etc.

### Editor & Analysis
- **Ballistic Coefficient Visual Editor**: Tray menu → "Open Editor" or run `main_editor.py` standalone; visually adjust 8 gun coefficients, mode (disabled/enabled/auto-click) and attachment combos with real-time trajectory preview
- **Scope Switch Preview**: Editor supports 1x/2x/3x scope switching and multi-scope overlay comparison
- **Preset Management**: Save/load/delete config presets (switch profiles by DPI/resolution/mouse model)
- **Lua Auto-Backup**: Editor automatically creates `.bak` backup on save
- **Ballistic Analysis**: multi-strategy bullet-hole detection (gray holes → green markers → OpenCV contours), full-magazine normalization and per-shot alignment, with a visual preview before saving

### Others
- **Voice Prompts for Key Actions**: Plays audio cues for recoil mode on/off, lock/unlock, and lock interception; supports volume control and per-event toggle
- Settings window with tab layout (Basic / Gun / Recognition / Voice / Crosshair)
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

### Attachment Cycling (When Caps Lock is ON)

| Combination               | Function           |
| ------------------------- | ------------------ |
| LAlt + Mouse Middle (G3)  | Cycle muzzle       |
| LCtrl + Mouse Middle (G3) | Cycle grip         |
| LShift + Mouse Middle (G3)| Cycle stock        |

Available attachment values:
- Muzzle: None / Compensator / Flash Hider / Suppressor / Muzzle Brake
- Grip: None / Vertical / Angled / Thumb / Half / Light
- Stock: None / Tactical / Heavy

### Scope Mode Switching (When Caps Lock is ON)

| Combination                 | Function      |
| --------------------------- | ------------- |
| RAlt + Mouse G5 (Forward)   | Switch to 2x  |
| RAlt + Mouse G4 (Back)      | Switch to 3x  |
| RCtrl + Mouse G5 (Forward)  | Switch to 1x  |

The current scope (1/2/3) is displayed at the top-left of the overlay.

### Recoil Mode Control

| Action                                          | Function                                       |
| ----------------------------------------------- | ---------------------------------------------- |
| Press Caps Lock (currently showing "None")      | Enable recoil mode, show default weapon (UMP5) |
| Press Caps Lock (currently showing weapon name) | Disable recoil mode, show "None"               |
| Press 1 key                                     | Enable recoil mode (same as Caps Lock when "None" is shown) |
| Press 2 key                                     | Disable recoil mode, show "None"               |
| Press G / 3 / 4 / 5 keys                        | Cancel recoil mode, show "None"                |
| Press Tab key                                   | Cancel recoil mode, show "None"                |
| Caps Lock OFF                                   | Show "None"                                    |
| Press RCtrl + Mouse G4 (Back)                   | Lock/Unlock weapon switching (overlay turns yellow when locked) |
| Press LCtrl + LAlt + Win                       | One-key reset of all state (weapon, scope, attachments, lock) |

### Stance Detection (In-Game Keys)

| Key           | Function                                                     |
| ------------- | ------------------------------------------------------------ |
| **C**         | Toggle crouch / stand                                         |
| **Z**         | Toggle prone / stand                                          |
| **Space**     | Break key — forces a reset to stand (jump, vault)             |

> Keys are remappable in Settings → Basic → Stance Detection. Stance detection must be enabled.

### On-Screen Center Crosshair

| Key                    | Function                                       |
| ---------------------- | ---------------------------------------------- |
| **Shift** (remappable) | Hold to show the crosshair (`hold` mode)        |
| Custom hotkey          | Toggle the crosshair when in `always` mode      |

## Stance Detection Details

Settings → **Basic** tab → "Stance Detection (Stand / Crouch / Prone)".

| Option                | Default   | Description                                                          |
| --------------------- | --------- | -------------------------------------------------------------------- |
| Enable stance detection | On      | When off, `rec_stance` keeps its default value                        |
| Ballistic table base  | `crouch`  | Base stance of the coefficient table (see conversion table below)    |
| Crouch key            | `C`       | Press once to crouch, press again to return to stand                 |
| Prone key             | `Z`       | Press once to prone, press again to return to stand                  |
| Break keys            | `Space`   | Jump/vault always returns to stand                                   |
| Track only when PUBG is in foreground | On | Avoids accidental triggers while typing on the desktop   |

**Base stance conversion** (the most common pitfall):

| Base      | Stand            | Crouch          | Prone                   |
| --------- | ---------------- | --------------- | ----------------------- |
| `stand`   | ×1.00            | ×crouch coeff.  | ×prone coeff.           |
| `crouch`  | ×(1 / crouch coeff.) | ×1.00       | ×(prone coeff. / crouch coeff.) |

With `crouch` base, **filling in 1.00 for the crouch coefficient means zero standing compensation** (recoil control will fail). The editor shows the live conversion for all three stances when you select a gun.

## Closed-Loop Calibration

Editor → **Tools → Closed-Loop Recoil Calibration…** (`Ctrl+C`).

**How it works**: while firing, the mouse itself does not move; recoil appears as the game world drifting relative to screen center. The calibrator captures the screen-center ROI at high frequency, tracks that drift with OpenCV template matching to obtain the recoil curve, splits it into per-shot increments by fire rate, and derives the compensation table through iterative learning.

**Steps**:

1. Open the editor and select the gun to calibrate (e.g. RPD)
2. "Tools → Closed-Loop Recoil Calibration…", configure fire interval, magazine size, bursts per round and max rounds
3. Switch to the game when prompted, and **stay standing with a red dot / holo** (scope and stance differences are handled by Lua-side coefficients)
4. Click "Confirm Fire" for each round as prompted and wait for it to finish
5. After 2~3 rounds the residual converges and the log reports the result
6. Results are applied to the editor's in-memory config (status bar shows "not saved") — **save manually** to write back to Lua

CLI alternative:

```bash
uv run python -m pubg_gun_control.recoil_calibrator --gun RPD
```

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
│   ├── tray_icon.py        # System tray module
│   ├── ballistic_data.py   # Ballistic data dataclasses (gun/attachment/config/preset)
│   ├── lua_parser.py       # Lua parser/serializer (canUse / attachmentConfig / gunNoStock)
│   ├── preset_manager.py   # Preset JSON persistence
│   └── editor_ui/          # Ballistic editor UI sub-package
│       ├── main_window.py       # Three-column main window
│       ├── gun_list_panel.py    # Gun list grouped by ammo
│       ├── gun_detail_panel.py  # 8 coefficients + mode editor
│       ├── attachment_panel.py  # Attachment combos + full-load coefficient
│       ├── trajectory_view.py   # Matplotlib trajectory chart
│       └── preset_dialog.py     # Preset naming dialog
├── main.py                 # Main program entry
├── main_editor.py          # Editor standalone entry
├── config.json             # Shortcut config + editor recent files
├── pubg_gun_control.spec   # PyInstaller build config
├── pyproject.toml          # Project config
└── test/
    ├── test_lua_parser.py        # Lua parser unit tests
    └── test_editor_integration.py # Editor integration tests
```

## Ballistic Coefficient Visual Editor

Launch via tray menu "Open Editor" or run `uv run python main_editor.py` standalone.

### Features

- **Three-column layout**: Gun list (grouped by ammo) on the left / 8 coefficients in the middle / trajectory chart on the right
- **8 coefficient editors**: Base, crouch, hold-breath, bare, full-load, prone, 2x scope, 3x scope (step 0.01)
- **Mode switch**: 0 disabled / 1 enabled / 2 auto-click
- **Attachment dropdowns**: 5 muzzle × 6 grip × 3 stock with real-time full-load coefficient
- **Trajectory preview**: Matplotlib render comparing current config vs bare
- **Scope switch**: Toggle 1x/2x/3x as main; overlay multiple scopes for comparison
- **Preset management**: Save as named presets (DPI / resolution / mouse model profiles)
- **Lua backup**: Auto-generate `<original>.bak` on save
- **Recent files**: Quick access to 5 most recent lua files in tray menu

### Tuning Workflow

1. File → Open `1.2.2-2024.5.20.-GHUB.-github.lua`
2. Select a gun on the left (ammo groups collapsible)
3. Adjust coefficients in the middle; chart updates in real time
4. Toggle 1x/2x/3x and overlay scopes to see recoil at each magnification
5. Preset → Save (e.g. `M762_1400dpi_1080p`)
6. File → Save → writes back to lua, GHUB auto-reloads

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
  ],
  "attachments": [
    {"modifier": "alt", "mouse_button": "middle", "category": "muzzle", "label": "Muzzle"},
    {"modifier": "ctrl", "mouse_button": "middle", "category": "grip", "label": "Grip"},
    {"modifier": "shift", "mouse_button": "middle", "category": "stock", "label": "Stock"}
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

You can open the visual configuration window via the "Settings" option in the system tray menu, and modifications will be saved automatically.
The settings window lets you edit the weapon display text and use checkboxes to configure whether each weapon supports muzzle/grip/stock attachments.

### Default Weapon Configuration

To change the default recoil weapon, edit `src/pubg_gun_control/config_manager.py`:

```python
def get_default_config() -> list[dict[str, str]]:
    return [
        {"modifier": "alt", "mouse_button": "backward", "text": "UMP5"},
        # Change the text of the first item to modify the default weapon
    ]
```

You also need to sync modify the `G_bind` configuration in `1.2.2-2024.5.20.-GHUB.-github.lua`.

## Changelog

### v1.3.0 (2026-10-10)
- **Added**: stance detection module `stance_tracker.py` — listens to C/Z/Space to infer stand/crouch/prone and passes it to the GHUB script via `rec_stance` so recoil coefficients follow the stance
  - press/release pairing eliminates Windows key auto-repeat (holding C toggles once)
  - break-key mechanism: jumping/vaulting forces a reset to stand
  - foreground-window focus filtering avoids desktop typing false triggers
  - new tray menu item "Reset Stance to Stand" for manual drift correction
  - new stance configuration block in Settings → Basic
- **Added**: closed-loop ballistic auto-calibration `recoil_calibrator.py` + wizard dialog `calibration_dialog.py`
  - ILC iterative learning: uncompensated baseline → compensated rounds → estimate pixel gain γ → converge in 2~3 rounds
  - mss high-frequency capture + OpenCV template matching to track world-reference drift
  - Editor entry "Tools → Closed-Loop Recoil Calibration…", runs in a QThread without blocking the UI, live log output
  - Results applied to in-memory config (marked dirty); writing back to Lua still goes through the normal save flow
- **Added**: on-screen center crosshair `crosshair_window.py` with cross/dot/circle/cross-dot shapes, configurable color and size
  - always-on / hold-a-key modes, follows the display under the mouse cursor in multi-monitor setups
  - always-on-top, click-through, tool-window style; new "Crosshair" tab in settings with live preview
- **Added**: overlay position can be unlocked and dragged, persisted as `overlay_position` in `config.json`
- **Added**: new `stance` and `crosshair` sections in `config.json`
- **Added**: new RPD weapon template; 4x and 6x scope templates
- **Tests**: added `test_stance_tracker.py`, `test_recoil_calibrator.py`, `test_calibration_dialog.py`, `test_lua_export_stance.py`
- **Fixed**: recognition results are now read via `loadLuaFile` global-variable injection, working around silent `rec.lua` read failures caused by the `io` library being unavailable in the GHUB sandbox

### v1.1.3 (2026-06-18)
- **Fix**: No voice prompts after packaging as exe; `pubg_gun_control.spec` now includes `voice/` in `Analysis.datas` so resources are extracted to `_MEIPASS/voice/` at runtime
- **New**: 0~100 volume slider in the settings window; uses `wave` + `audioop` to dynamically adjust volume (falls back to native playback when `audioop` is unavailable)
- **New**: Per-event toggles for all 5 voice prompts (recoil on/off, lock on/off, lock intercept) with a "Preview" button per event
- **New**: `config.json` adds `voice_volume` and `voice_event_enabled` fields to persist these settings

### v1.1.2 (2026-06-18)
- **New**: Voice prompts for key actions; plays cues for recoil mode on/off, lock/unlock, and lock interception
- **New**: "Enable Voice Prompts" checkbox in the settings window; voice toggle is persisted to `config.json`
- **Improve**: New voice prompt interrupts currently playing prompt, avoiding delayed playback during rapid actions
- **New**: `voice/` directory for WAV files, `src/pubg_gun_control/voice_prompt.py` provides async playback wrapper
- **Test**: Added `test/test_voice_prompt.py` covering voice playback and lock interception logic

### v1.1.1 (2026-06-18)
- **New**: Ballistic coefficient visual editor, launched via tray menu "Open Editor" or standalone `main_editor.py`
- **New**: 8 gun coefficients (base / crouch / hold-breath / bare / full-load / prone / 2x scope / 3x scope) editable visually
- **New**: Mode switch (0 disabled / 1 enabled / 2 auto-click) dropdown
- **New**: Attachment dropdowns (5 muzzle × 6 grip × 3 stock) with auto-computed full-load coefficient
- **New**: Matplotlib trajectory preview with real-time visual feedback
- **New**: 1x/2x/3x scope switch and multi-scope overlay comparison
- **New**: Preset management (save/load/delete) by DPI / resolution / mouse model
- **New**: Lua file auto-backup (generates `<original>.bak` on save)
- **New**: Recent files list (5 entries) with tray menu quick access
- **Dependency**: PySide6 + matplotlib

### v1.10 (2026-06-18)
- **New**: Attachment cycling for muzzle / grip / stock; triggered by LAlt / LCtrl / LShift + mouse middle button
- **New**: Scope mode switching; RAlt + mouse G5/G4 toggles 2x/3x scope and RCtrl + mouse G5 switches back to 1x; current scope is shown at the top-left of the overlay
- **New**: One-key reset; LCtrl + LAlt + Win resets weapon, scope, attachments and lock state
- **New**: Number keys 1/2 now control recoil mode (1 enables, 2 disables)
- **New**: Settings window supports checkboxes for per-weapon attachment support; unsupported attachments are auto-reset to "None" when switching weapons
- **Improve**: Overlay now displays scope + weapon name + attachments
- **Improve**: Lock shortcut changed from Ctrl+Alt to RCtrl+Mouse G4 to avoid conflicts with recoil combos
- **Refactor**: Attachment / scope / reset logic centralized in `InputListener`; configuration data moved to `config.json`

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
