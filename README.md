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
4. Adjust parameters if needed:

    * `mult_x` / `mult_y`
    * `tol_x` / `tol_y`
    * aspect ratio
    * gathering speed
    * no-stamina mode
5. Press **Start**
6. The script begins gathering automatically
7. Press **Stop** at any time

---

## ⚙️ Parameters (summary)

| Parameter           | Description                                                  |
|---------------------|--------------------------------------------------------------|
| `mult_x / mult_y`   | movement multiplier (how much character moves per step)      |
| `tol_x / tol_y`     | tolerance for size of resource                               |
| `Aspect Ratio`      | must match your game resolution                              |
| `Gathering Speed`   | controls timing between actions. Depends on life skill level |
| `No-stamina mode`   | Gathering in normal mode. Without Focus                      |
| `Run back to start` | returns to initial position after cycle                      |

---

## ⚠️ Disclaimer

This tool simulates user input.
Use at your own risk. The author is not responsible for any consequences or game ToS violations.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.