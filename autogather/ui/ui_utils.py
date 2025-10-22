import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


def _blend(c1, c2, a=0.5):
    # hex color blend: a from c2 onto c1
    c1 = c1.lstrip('#')
    c2 = c2.lstrip('#')
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 * (1 - a) + r2 * a)
    g = int(g1 * (1 - a) + g2 * a)
    b = int(b1 * (1 - a) + b2 * a)
    return f"#{r:02x}{g:02x}{b:02x}"


def _palette(dark: bool):
    if dark:
        BG = "#0f1115"
        SURF = "#171a21"
        CARD = "#1d212a"
        TXT = "#e6e6e6"
        MUT = "#a8b0bd"
        ACC = "#3b82f6"
        BRD = "#2a2f3a"
    else:
        BG = "#f6f7fb"
        SURF = "#ffffff"
        CARD = "#ffffff"
        TXT = "#1f2937"
        MUT = "#6b7280"
        ACC = "#2563eb"
        BRD = "#e5e7eb"
    return dict(BG=BG, SURF=SURF, CARD=CARD, TXT=TXT, MUT=MUT, ACC=ACC, BRD=BRD)


def _apply_style(root: tk.Tk, dark: bool):
    pal = _palette(dark)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=pal["BG"])

    # ------ Fonts
    base = tkfont.Font(family="Segoe UI", size=10)
    base_b = tkfont.Font(family="Segoe UI Semibold", size=10)
    title = tkfont.Font(family="Segoe UI Semibold", size=15)
    small = tkfont.Font(family="Segoe UI", size=9)

    root.option_add("*Font", base)
    root.option_add("*TCombobox*Listbox.Font", base)
    root.option_add("*TSpinbox*Listbox.Font", base)

    # ------ Base
    style.configure(".", background=pal["BG"], foreground=pal["TXT"])
    style.configure("TFrame", background=pal["BG"])
    style.configure("TLabel", background=pal["BG"], foreground=pal["TXT"])
    style.configure("TLabelframe", background=pal["BG"], bordercolor=pal["BRD"])
    style.configure("TLabelframe.Label", background=pal["BG"], foreground=pal["MUT"], font=base_b)
    style.configure("TSeparator", background=pal["BRD"])

    # ------ Cards
    style.configure("Card.TFrame", background=pal["CARD"], borderwidth=1, relief="solid", bordercolor=pal["BRD"])
    style.configure("Card.TLabel", background=pal["CARD"], foreground=pal["TXT"])
    style.configure("Card.Muted.TLabel", background=pal["CARD"], foreground=pal["MUT"])
    style.configure("Card.Section.TLabel", background=pal["CARD"], foreground=pal["TXT"], font=base_b)

    # ------ Checkbuttons (visible in dark)
    style.configure("Card.TCheckbutton", background=pal["CARD"], foreground=pal["TXT"])
    style.map(
        "Card.TCheckbutton",
        background=[("active", pal["CARD"])],
        foreground=[("active", pal["TXT"]), ("selected", pal["TXT"]), ("disabled", pal["MUT"])],
        indicatorcolor=[("!disabled", pal["ACC"]), ("disabled", pal["BRD"])],
    )

    # ------ Buttons
    btn = pal["ACC"]
    hover = _blend(pal["ACC"], "#ffffff" if not dark else "#000000", 0.12)
    style.configure("Primary.TButton", background=btn, foreground="#fff", padding=(12, 8), borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", hover), ("pressed", hover)],
              foreground=[("disabled", _blend("#ffffff", pal["CARD"], 0.5))])

    style.configure("TButton", background=pal["SURF"], foreground=pal["TXT"], borderwidth=1, padding=(10, 7))
    style.map("TButton",
              background=[("active", _blend(pal["SURF"], pal["ACC"], 0.08))],
              foreground=[("disabled", pal["MUT"])])

    # ------ Inputs (Combobox / Spinbox) — high contrast & readable
    field_bg = pal["SURF"]  # control field bg
    field_fg = pal["TXT"]  # normal text
    hint_fg = pal["MUT"]  # disabled/muted text
    sel_bg = _blend(pal["ACC"], field_bg, 0.85)  # selection background
    sel_fg = field_fg

    # Combobox (entry area)
    style.configure(
        "Drop.TCombobox",
        fieldbackground=field_bg,
        foreground=field_fg,
        background=pal["CARD"],
        bordercolor=pal["BRD"],
        arrowsize=14,
        arrowcolor=hint_fg,
    )
    style.map(
        "Drop.TCombobox",
        fieldbackground=[("readonly", field_bg), ("disabled", field_bg)],
        foreground=[("readonly", field_fg), ("disabled", hint_fg)],
        selectbackground=[("!disabled", sel_bg)],
        selectforeground=[("!disabled", sel_fg)],
        arrowcolor=[("active", pal["ACC"]), ("!active", hint_fg)]
    )
    # Popup listbox colors for Combobox
    root.option_add("*TCombobox*Listbox*Background", field_bg)
    root.option_add("*TCombobox*Listbox*Foreground", field_fg)
    root.option_add("*TCombobox*Listbox*selectBackground", sel_bg)
    root.option_add("*TCombobox*Listbox*selectForeground", sel_fg)
    root.option_add("*TCombobox*insertBackground", field_fg)  # caret color

    # Spinbox (numbers)
    style.configure(
        "Num.TSpinbox",
        fieldbackground=field_bg,
        foreground=field_fg,
        bordercolor=pal["BRD"],
        background=pal["CARD"],
        arrowsize=14,
    )
    style.map(
        "Num.TSpinbox",
        fieldbackground=[("readonly", field_bg), ("disabled", field_bg)],
        foreground=[("readonly", field_fg), ("disabled", hint_fg)]
    )
    root.option_add("*TSpinbox*insertBackground", field_fg)

    # ------ Headers / Status / Links
    style.configure("Header.TFrame", background=pal["BG"])
    style.configure("Title.TLabel", background=pal["BG"], foreground=pal["TXT"], font=title)
    style.configure("Subtitle.TLabel", background=pal["BG"], foreground=pal["MUT"], font=small)
    style.configure("Status.TLabel", background=pal["CARD"], foreground=pal["MUT"], font=small)

    # link-like label (for GitHub)
    style.configure("Link.TLabel", background=pal["BG"], foreground=pal["ACC"])


def _card(parent, **grid_kwargs):
    f = ttk.Frame(parent, style="Card.TFrame", padding=14)
    f.grid(**grid_kwargs)
    for i in range(4):
        f.columnconfigure(i, weight=1)
    return f


def _github_icon(dark: bool) -> tk.PhotoImage:
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(here, "assets")
    fname = "github_dark.png" if dark else "github_light.png"
    path = os.path.join(assets, fname)
    return tk.PhotoImage(file=path)
