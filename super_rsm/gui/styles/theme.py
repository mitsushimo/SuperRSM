"""
super_rsm/gui/styles/theme.py

Platform-aware typography and TTK widget theme configuration for SuperRSM GUI.
"""

import platform
import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple

from super_rsm.gui.styles.palette import PALETTE


def get_ui_fonts() -> Dict[str, Tuple]:
    """Return platform-appropriate font tuples for UI typography."""
    system = platform.system()
    if system == "Windows":
        base = "Segoe UI"
        mono = "Consolas"
    elif system == "Darwin":
        base = "SF Pro Text"
        mono = "Menlo"
    else:
        base = "DejaVu Sans"
        mono = "DejaVu Sans Mono"
    return {
        "title": (base, 13, "bold"),
        "subtitle": (base, 9),
        "section": (base, 9, "bold"),
        "body": (base, 9),
        "body_bold": (base, 9, "bold"),
        "small": (base, 8),
        "small_bold": (base, 8, "bold"),
        "kpi_value": (base, 14, "bold"),
        "kpi_label": (base, 8, "bold"),
        "mono": (mono, 9),
        "mono_bold": (mono, 9, "bold"),
    }


def configure_ttk_styles(root: tk.Misc) -> Dict[str, Tuple]:
    """Configure custom TTK styles on root widget and return UI font dictionary."""
    fonts = get_ui_fonts()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    if hasattr(root, "configure"):
        try:
            root.configure(bg=PALETTE["bg_main"])
        except tk.TclError:
            pass

    style.configure(
        ".",
        background=PALETTE["bg_main"],
        foreground=PALETTE["text_main"],
        font=fonts["body"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border_light"],
        darkcolor=PALETTE["border"],
    )

    style.configure("TFrame", background=PALETTE["bg_main"])
    style.configure("Card.TFrame", background=PALETTE["bg_card"])
    style.configure("Subtle.TFrame", background=PALETTE["bg_subtle"])
    style.configure("Header.TFrame", background=PALETTE["bg_header"])

    style.configure("TLabel", background=PALETTE["bg_main"], foreground=PALETTE["text_main"], font=fonts["body"])
    style.configure("Card.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_main"], font=fonts["body"])
    style.configure("CardBold.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_main"], font=fonts["body_bold"])
    style.configure("Muted.TLabel", background=PALETTE["bg_main"], foreground=PALETTE["text_muted"], font=fonts["small"])
    style.configure("CardMuted.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_muted"], font=fonts["small"])
    style.configure("HeaderTitle.TLabel", background=PALETTE["bg_header"], foreground="#FFFFFF", font=fonts["title"])
    style.configure("HeaderSub.TLabel", background=PALETTE["bg_header"], foreground="#94A3B8", font=fonts["subtitle"])

    style.configure(
        "TLabelframe",
        background=PALETTE["bg_card"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=PALETTE["bg_card"],
        foreground=PALETTE["accent"],
        font=fonts["section"],
        padding=(4, 0),
    )

    style.configure(
        "TButton",
        background="#FFFFFF",
        foreground=PALETTE["text_main"],
        bordercolor=PALETTE["border"],
        lightcolor="#FFFFFF",
        darkcolor=PALETTE["border"],
        font=fonts["body"],
        padding=(10, 5),
        relief="solid",
        borderwidth=1,
    )
    style.map(
        "TButton",
        background=[("active", PALETTE["bg_main"]), ("pressed", PALETTE["border_light"]), ("disabled", PALETTE["bg_subtle"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )

    style.configure("Small.TButton", font=fonts["small"], padding=(6, 2))

    style.configure(
        "Primary.TButton",
        background=PALETTE["accent"],
        foreground="#FFFFFF",
        bordercolor=PALETTE["accent"],
        lightcolor=PALETTE["accent"],
        darkcolor=PALETTE["accent_hover"],
        font=fonts["body_bold"],
        padding=(12, 7),
    )
    style.map(
        "Primary.TButton",
        background=[("active", PALETTE["accent_hover"]), ("pressed", "#1E40AF"), ("disabled", "#94A3B8")],
        foreground=[("disabled", "#F1F5F9")],
    )

    style.configure(
        "Secondary.TButton",
        background="#EFF6FF",
        foreground=PALETTE["accent"],
        bordercolor="#BFDBFE",
        lightcolor="#EFF6FF",
        darkcolor="#BFDBFE",
        font=fonts["body_bold"],
        padding=(12, 6),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", PALETTE["accent_light"]), ("pressed", "#BFDBFE"), ("disabled", PALETTE["bg_subtle"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )

    style.configure(
        "Danger.TButton",
        background="#FEF2F2",
        foreground=PALETTE["danger"],
        bordercolor="#FECACA",
        lightcolor="#FEF2F2",
        darkcolor="#FECACA",
        font=fonts["small"],
        padding=(7, 3),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#FEE2E2"), ("pressed", "#FECACA"), ("disabled", PALETTE["bg_subtle"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )

    for widget_style in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(
            widget_style,
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            foreground=PALETTE["text_main"],
            bordercolor=PALETTE["border"],
            lightcolor="#FFFFFF",
            darkcolor=PALETTE["border"],
            insertcolor=PALETTE["text_main"],
            padding=4,
        )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#FFFFFF"), ("disabled", PALETTE["bg_subtle"])],
        selectbackground=[("readonly", "#FFFFFF")],
        selectforeground=[("readonly", PALETTE["text_main"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", PALETTE["bg_subtle"]), ("disabled", PALETTE["bg_subtle"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )
    style.map(
        "TSpinbox",
        fieldbackground=[("disabled", PALETTE["bg_subtle"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )

    style.configure("TCheckbutton", background=PALETTE["bg_card"], foreground=PALETTE["text_main"], font=fonts["body"])
    style.map("TCheckbutton", background=[("active", PALETTE["bg_card"])], foreground=[("disabled", PALETTE["text_muted"])])

    style.configure("TNotebook", background=PALETTE["bg_main"], borderwidth=0, tabmargins=(0, 2, 0, 0))
    style.configure(
        "TNotebook.Tab",
        background=PALETTE["border_light"],
        foreground=PALETTE["text_secondary"],
        font=fonts["body_bold"],
        padding=(14, 6),
        borderwidth=1,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["bg_card"]), ("active", "#E2E8F0")],
        foreground=[("selected", PALETTE["accent"]), ("active", PALETTE["text_main"])],
    )

    style.configure(
        "Treeview",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground=PALETTE["text_main"],
        rowheight=25,
        font=fonts["body"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["bg_subtle"],
        foreground=PALETTE["text_secondary"],
        font=fonts["small_bold"],
        padding=(6, 5),
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", PALETTE["border_light"])])
    style.map("Treeview", background=[("selected", PALETTE["accent_light"])], foreground=[("selected", PALETTE["text_main"])])

    style.configure("TPanedwindow", background=PALETTE["bg_main"])
    style.configure("Sash", sashthickness=6, gripcount=10)

    return fonts

