# Blue Protocol: Star Resonance - Auto gathering
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

GUI-based automation tool for gathering resources in **Blue Protocol: Star Resonance**.  
The tool simulates user input (mouse/keyboard) and detects on-screen elements using images from the `/resources`
folder.  
It does **not** read or modify game memory and does **not** inject into the client.

---

## ✨ Features

- Automatic resource gathering loop
- Per-resource configurable parameters (tolerances, multipliers, focus rules)
- ROI-based prompt detection (`F` interaction)
- Customizable aspect ratio for UI scaling
- No-stamina mode (only “Gathering” actions)
- Option to return to start after the route
- Adjustable gathering speed
- Full GUI — no console setup needed

---

### 📌 Requirements

| Component | Version     |
|-----------|-------------|
| Windows   | 10/11       |
| Python    | 3.10+       |
| Game mode | Full Screen |

---

### 🚀 Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r autogather/requirements.txt
```

---

## ▶️ Launch

```bash
python -m autogather
```

A window will open with all UI controls.

---

## 🧩 Resource Folder Structure

Each folder under `/resources` must contain:

```
focused/
gathering/
selector/
```

These images are used to detect the correct UI state on screen.

---

## 🕹️ How to Use

1. Select your `/resources` directory
2. Pick a resource from the dropdown
3. Choose the game window
4. Choose the aspect ratio
5. Adjust parameters if needed:
    * `mult_x` / `mult_y`
    * `tol_x` / `tol_y`
    * gathering speed
    * no-stamina mode
    * don't move
    * run back to start
6. Press **Start**
7. The script begins gathering automatically
8. Press **Stop** at any time

---

## ⚙️ Parameters (summary)

| Parameter           | Description                                                  |
|---------------------|--------------------------------------------------------------|
| `mult_x / mult_y`   | Movement multiplier (need when change angle of 'Y' or zoom)  |
| `tol_x / tol_y`     | Tolerance for size of resource                               |
| `Aspect Ratio`      | Must match your game resolution                              |
| `Gathering Speed`   | Controls timing between actions. Depends on life skill level |
| `No-stamina mode`   | Gathering in normal mode. Without Focus                      |
| `Don't move`        | Stay in one place and gather resource                        |
| `Run back to start` | Returns to initial position after cycle                      |

---

## Presets (Save / Load)

You can save your current settings per resource using the **“💾 Save preset”** button (bottom bar).

* On first save, the app creates `presets.json` in the project root.
  If the file doesn’t exist, it’s initialized with **defaults for all resources**.
* Each time you press **Save preset**, the settings for the **currently selected resource** are updated.
* Presets are auto-loaded on start (if present).

**Saved fields per resource**

* `mult_x`, `mult_y` — movement multipliers
* `tol_x`, `tol_y` — scan tolerances
* `want_gathering`, `dont_move`, `move_back_to_start` — behavior flags
* `gathering_speed` — `SLOW | NORMAL | FAST`
* Global: `aspect_ratio` (e.g. `"21:9", "16:9", "4:3"`)

**Example `presets.json`**

```json
{
  "andra_enigmite": {
    "mult_x": 1.0,
    "mult_y": 1.0,
    "tol_x": 150,
    "tol_y": 150,
    "want_gathering": true,
    "dont_move": false,
    "move_back_to_start": false,
    "gathering_speed": "FAST"
  },
  "aspect_ratio": "21:9",
  "_updated_at": "2025-10-24 12:43:28"
}
```

---

## ⚠️ Disclaimer

This tool simulates user input.
Use at your own risk. The author is not responsible for any consequences or game ToS violations.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.