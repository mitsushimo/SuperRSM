import importlib.util
import json
import platform
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import pandas as pd

from scipy.optimize import LinearConstraint
import rsm_backend


# =============================================================================
# UI Theme & Color Palette Constants
# =============================================================================
PALETTE = {
    "bg_main": "#F1F5F9",       # Slate 100 - main window background
    "bg_card": "#FFFFFF",       # Pure white - card / panel surface
    "bg_subtle": "#F8FAFC",     # Slate 50 - subtle secondary surface
    "bg_header": "#0F172A",     # Slate 900 - top header bar
    "text_main": "#0F172A",     # Slate 900 - primary text
    "text_secondary": "#334155",# Slate 700 - secondary text
    "text_muted": "#64748B",    # Slate 500 - muted captions / hints
    "accent": "#2563EB",        # Blue 600 - primary brand / action
    "accent_hover": "#1D4ED8",  # Blue 700 - hover state
    "accent_light": "#DBEAFE",  # Blue 100 - soft selection highlight
    "border": "#CBD5E1",        # Slate 300 - widget & card borders
    "border_light": "#E2E8F0",  # Slate 200 - subtle dividers
    "success": "#16A34A",       # Green 600 - converged / satisfied
    "success_bg": "#DCFCE7",    # Green 100
    "warning": "#D97706",       # Amber 600 - warning state
    "warning_bg": "#FEF3C7",    # Amber 100
    "danger": "#DC2626",        # Red 600 - destructive / violated
    "danger_hover": "#B91C1C",  # Red 700
}

COMMON_CMAPS = [
    "plasma",
    "viridis",
    "inferno",
    "magma",
    "cividis",
    "coolwarm",
    "YlGnBu",
    "Spectral",
    "RdYlBu_r",
    "turbo",
]

COMMON_LINESTYLES = ["--", "-", ":", "-."]
COMMON_MARKERS = ["o", "s", "^", "v", "D", "P", "*", "X", "x", "+"]


def get_ui_fonts():
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


def configure_ttk_styles(root):
    fonts = get_ui_fonts()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    root.configure(bg=PALETTE["bg_main"])

    # Base widget defaults
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

    # Labels
    style.configure("TLabel", background=PALETTE["bg_main"], foreground=PALETTE["text_main"], font=fonts["body"])
    style.configure("Card.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_main"], font=fonts["body"])
    style.configure("CardBold.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_main"], font=fonts["body_bold"])
    style.configure("Muted.TLabel", background=PALETTE["bg_main"], foreground=PALETTE["text_muted"], font=fonts["small"])
    style.configure("CardMuted.TLabel", background=PALETTE["bg_card"], foreground=PALETTE["text_muted"], font=fonts["small"])
    style.configure("HeaderTitle.TLabel", background=PALETTE["bg_header"], foreground="#FFFFFF", font=fonts["title"])
    style.configure("HeaderSub.TLabel", background=PALETTE["bg_header"], foreground="#94A3B8", font=fonts["subtitle"])

    # LabelFrames (Section cards)
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

    # Buttons
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

    style.configure(
        "Small.TButton",
        font=fonts["small"],
        padding=(6, 2),
    )

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

    # Entries, Spinboxes, Comboboxes
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

    # Checkbuttons
    style.configure(
        "TCheckbutton",
        background=PALETTE["bg_card"],
        foreground=PALETTE["text_main"],
        font=fonts["body"],
    )
    style.map(
        "TCheckbutton",
        background=[("active", PALETTE["bg_card"])],
        foreground=[("disabled", PALETTE["text_muted"])],
    )

    # Notebook & Tabs
    style.configure(
        "TNotebook",
        background=PALETTE["bg_main"],
        borderwidth=0,
        tabmargins=(0, 2, 0, 0),
    )
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

    # Treeview
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
    style.map(
        "Treeview.Heading",
        background=[("active", PALETTE["border_light"])],
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["accent_light"])],
        foreground=[("selected", PALETTE["text_main"])],
    )

    # PanedWindow
    style.configure("TPanedwindow", background=PALETTE["bg_main"])
    style.configure("Sash", sashthickness=6, gripcount=10)

    return fonts


def format_linear_expression(coeffs_dict, operator, bound):
    """
    Format a linear combination expression string from a dictionary of variable coefficients,
    comparison operator, and RHS bound value.
    """
    terms = []
    for col, coeff in coeffs_dict.items():
        if abs(coeff) < 1e-12:
            continue
        coeff_str = f"{coeff:g}"
        terms.append((col, coeff, coeff_str))

    if not terms:
        return f"(No non-zero terms) {operator} {bound:g}"

    expr_parts = []
    for i, (col, coeff, coeff_str) in enumerate(terms):
        if i == 0:
            if coeff == 1.0:
                expr_parts.append(f"{col}")
            elif coeff == -1.0:
                expr_parts.append(f"-{col}")
            else:
                expr_parts.append(f"{coeff_str}*{col}")
        else:
            if coeff > 0:
                if coeff == 1.0:
                    expr_parts.append(f"+ {col}")
                else:
                    expr_parts.append(f"+ {coeff_str}*{col}")
            else:
                if coeff == -1.0:
                    expr_parts.append(f"- {col}")
                else:
                    abs_str = f"{abs(coeff):g}"
                    expr_parts.append(f"- {abs_str}*{col}")

    return f"{' '.join(expr_parts)} {operator} {bound:g}"


class LinearConstraintDialog(tk.Toplevel):
    """
    Modal dialog allowing the user to specify a linear combination of input variables
    and a constraint condition (<=, >=, == bound).
    """
    def __init__(self, parent, input_cols, existing_constraint=None, on_save_callback=None):
        super().__init__(parent)
        self.title("Edit Linear Constraint" if existing_constraint else "Add Linear Constraint")
        self.geometry("560x540")
        self.minsize(480, 440)
        self.configure(bg=PALETTE["bg_main"])
        self.transient(parent)
        self.grab_set()

        self.fonts = get_ui_fonts()
        self.input_cols = input_cols
        self.existing_constraint = existing_constraint
        self.on_save_callback = on_save_callback

        self.coeff_vars = {}
        self.operator_var = tk.StringVar(
            value=existing_constraint.get("operator", "<=") if existing_constraint else "<="
        )
        self.bound_var = tk.StringVar(
            value=f"{existing_constraint.get('bound', 0.0):g}" if existing_constraint else ""
        )
        self.preview_var = tk.StringVar(value="")

        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        container = ttk.Frame(self, padding="12")
        container.pack(fill=tk.BOTH, expand=True)

        # Bottom Action Buttons (Anchored first to always remain visible)
        btn_frame = ttk.Frame(container)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        save_btn = ttk.Button(
            btn_frame, text="Save Constraint", style="Primary.TButton", command=self.on_save
        )
        save_btn.pack(side=tk.RIGHT, padx=(6, 0))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT)

        # Expression Preview (Anchored above buttons)
        preview_lf = ttk.LabelFrame(container, text="Live Expression Preview", padding="8")
        preview_lf.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 6))

        preview_lbl = ttk.Label(
            preview_lf,
            textvariable=self.preview_var,
            foreground=PALETTE["accent"],
            background=PALETTE["bg_card"],
            wraplength=510,
            font=self.fonts["mono_bold"],
        )
        preview_lbl.pack(anchor=tk.W)

        # Condition Frame (Anchored above preview)
        cond_lf = ttk.LabelFrame(container, text="Constraint Condition", padding="8")
        cond_lf.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 6))

        ttk.Label(cond_lf, text="Relation:", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        op_combo = ttk.Combobox(
            cond_lf,
            textvariable=self.operator_var,
            values=["<=", ">=", "=="],
            state="readonly",
            width=6,
        )
        op_combo.pack(side=tk.LEFT, padx=(0, 18))
        op_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        ttk.Label(cond_lf, text="Bound Value (RHS):", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        bound_entry = ttk.Entry(cond_lf, textvariable=self.bound_var, width=16)
        bound_entry.pack(side=tk.LEFT)
        self.bound_var.trace_add("write", lambda *args: self.update_preview())

        # Top Instruction Label
        info_lbl = ttk.Label(
            container,
            text="Define a linear combination of input variables (∑ cᵢ · xᵢ) and set its boundary condition:",
            wraplength=520,
        )
        info_lbl.pack(side=tk.TOP, anchor=tk.W, pady=(0, 6))

        # Scrollable Coefficients Frame (Expands to fill remaining middle space)
        coeff_lf = ttk.LabelFrame(container, text="Variable Coefficients (cᵢ)", padding="8")
        coeff_lf.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 6))

        canvas = tk.Canvas(
            coeff_lf,
            borderwidth=0,
            highlightthickness=0,
            background=PALETTE["bg_card"],
            height=130,
        )
        scrollbar = ttk.Scrollbar(coeff_lf, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Card.TFrame")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_win_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(canvas_win_id, width=e.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel scrolling support for variable list
        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(scrollable_frame, text="Variable", style="CardBold.TLabel").grid(
            row=0, column=0, padx=10, pady=(2, 6), sticky=tk.W
        )
        ttk.Label(scrollable_frame, text="Coefficient (cᵢ)", style="CardBold.TLabel").grid(
            row=0, column=1, padx=10, pady=(2, 6), sticky=tk.W
        )

        existing_coeffs = self.existing_constraint.get("coeffs", {}) if self.existing_constraint else {}

        for i, col in enumerate(self.input_cols):
            lbl = ttk.Label(scrollable_frame, text=col, style="Card.TLabel")
            lbl.grid(row=i + 1, column=0, padx=10, pady=4, sticky=tk.W)
            lbl.bind("<MouseWheel>", _on_mousewheel)

            val = existing_coeffs.get(col, 0.0)
            val_str = f"{val:g}" if self.existing_constraint else ("1" if i == 0 else "0")
            var = tk.StringVar(value=val_str)
            var.trace_add("write", lambda *args: self.update_preview())
            self.coeff_vars[col] = var

            entry = ttk.Entry(scrollable_frame, textvariable=var, width=18)
            entry.grid(row=i + 1, column=1, padx=10, pady=4, sticky=tk.W)
            entry.bind("<MouseWheel>", _on_mousewheel)

    def update_preview(self):
        coeffs = {}
        for col, var in self.coeff_vars.items():
            text = var.get().strip()
            try:
                coeffs[col] = float(text) if text else 0.0
            except ValueError:
                coeffs[col] = 0.0

        op = self.operator_var.get()
        bound_text = self.bound_var.get().strip()
        try:
            bound_val = float(bound_text) if bound_text else 0.0
            bound_str = f"{bound_val:g}"
        except ValueError:
            bound_str = bound_text if bound_text else "?"

        non_zeros = {k: v for k, v in coeffs.items() if abs(v) > 1e-12}
        if not non_zeros:
            self.preview_var.set("(All coefficients are 0 - enter at least one non-zero coefficient)")
        else:
            try:
                b_val = float(bound_str)
                self.preview_var.set(format_linear_expression(coeffs, op, b_val))
            except ValueError:
                parts = []
                for k, v in non_zeros.items():
                    parts.append(f"{v:g}*{k}")
                self.preview_var.set(f"{' + '.join(parts)} {op} {bound_str}")

    def on_save(self):
        coeffs = {}
        for col, var in self.coeff_vars.items():
            text = var.get().strip()
            if not text:
                coeffs[col] = 0.0
                continue
            try:
                coeffs[col] = float(text)
            except ValueError:
                messagebox.showerror("Error", f"Invalid coefficient for '{col}'. Please enter a valid number.", parent=self)
                return

        if not any(abs(v) > 1e-12 for v in coeffs.values()):
            messagebox.showerror("Error", "At least one variable coefficient must be non-zero.", parent=self)
            return

        bound_text = self.bound_var.get().strip()
        if not bound_text:
            messagebox.showerror("Error", "Please enter a numeric bound value.", parent=self)
            return

        try:
            bound_val = float(bound_text)
        except ValueError:
            messagebox.showerror("Error", "Invalid bound value. Please enter a valid number.", parent=self)
            return

        op = self.operator_var.get()
        expr_str = format_linear_expression(coeffs, op, bound_val)

        constraint_data = {
            "coeffs": coeffs,
            "operator": op,
            "bound": bound_val,
            "expression_str": expr_str
        }

        if self.on_save_callback:
            self.on_save_callback(constraint_data)

        self.destroy()


class RSMGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Super RSM — Response Surface Optimization & Visualization")
        self.geometry("1160x820")
        self.minsize(940, 680)

        self.fonts = configure_ttk_styles(self)

        self.df = None
        self.bound_entries = {}
        self.eval_entries = {}
        self.eval_history = []
        self.linear_constraints = []
        self.previous_input_cols = []
        self.result = None
        self.current_input_cols = None
        self.current_output_col = None
        self.fitted_model_signature = None
        self.last_opt_report_text = ""
        self.opt_params_dict = {}
        self.plot_config_win = None

        self.create_widgets()

    def create_widgets(self):
        # =====================================================================
        # Top Header & Dataset Bar
        # =====================================================================
        header_bar = ttk.Frame(self, style="Header.TFrame", padding=(16, 10))
        header_bar.pack(fill=tk.X)

        title_box = ttk.Frame(header_bar, style="Header.TFrame")
        title_box.pack(side=tk.LEFT)
        ttk.Label(
            title_box,
            text="Super RSM",
            style="HeaderTitle.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Label(
            title_box,
            text="  |  Multi-Method Response Surface Modeling & Constrained Optimization",
            style="HeaderSub.TLabel",
        ).pack(side=tk.LEFT, pady=(2, 0))

        # Dataset Status Pill in Header
        self.dataset_badge_var = tk.StringVar(value="No dataset loaded")
        self.dataset_badge_lbl = tk.Label(
            header_bar,
            textvariable=self.dataset_badge_var,
            bg="#1E293B",
            fg="#94A3B8",
            font=self.fonts["small_bold"],
            padx=10,
            pady=3,
        )
        self.dataset_badge_lbl.pack(side=tk.RIGHT)

        # =====================================================================
        # Main Container
        # =====================================================================
        main_frame = ttk.Frame(self, padding=(12, 10, 12, 6))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. File Selection Bar ---
        file_frame = ttk.LabelFrame(main_frame, text="1. Dataset Source", padding=(10, 6))
        file_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(file_frame, text="Data File:", style="CardBold.TLabel").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(
            file_frame, textvariable=self.file_path_var, state="readonly"
        )
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(
            file_frame,
            text="Browse & Load...",
            style="Secondary.TButton",
            command=self.browse_file,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            file_frame,
            text="Reload",
            command=lambda: self.load_data(show_popup=False),
        ).pack(side=tk.LEFT)

        # --- Master Horizontal Split-Pane ---
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(paned, padding=(0, 0, 6, 0))
        right_pane = ttk.Frame(paned, padding=(6, 0, 0, 0))
        paned.add(left_pane, weight=11)
        paned.add(right_pane, weight=14)

        # =====================================================================
        # LEFT PANE: Configuration Deck (Steps 2 - 5 + Actions)
        # =====================================================================

        # --- 2. Column Selection ---
        col_frame = ttk.LabelFrame(left_pane, text="2. Select Variables", padding=(10, 8))
        col_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        col_frame.columnconfigure(0, weight=3)
        col_frame.columnconfigure(1, weight=2)
        col_frame.rowconfigure(1, weight=1)

        # Input Columns header + quick buttons
        input_hdr = ttk.Frame(col_frame, style="Card.TFrame")
        input_hdr.grid(row=0, column=0, sticky=tk.EW, padx=(0, 8), pady=(0, 4))
        ttk.Label(
            input_hdr, text="Input Factors (Multi-select):", style="CardBold.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(
            input_hdr,
            text="Clear",
            style="Small.TButton",
            command=self.clear_input_selection,
        ).pack(side=tk.RIGHT, padx=(3, 0))
        ttk.Button(
            input_hdr,
            text="Select All",
            style="Small.TButton",
            command=self.select_all_inputs,
        ).pack(side=tk.RIGHT)

        # Input Listbox + Scrollbar
        lb_container = tk.Frame(
            col_frame,
            bg=PALETTE["border"],
            bd=1,
            relief=tk.FLAT,
        )
        lb_container.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 8))
        lb_scroll = ttk.Scrollbar(lb_container, orient=tk.VERTICAL)
        self.input_listbox = tk.Listbox(
            lb_container,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=4,
            bg="#FFFFFF",
            fg=PALETTE["text_main"],
            selectbackground=PALETTE["accent_light"],
            selectforeground=PALETTE["accent"],
            highlightthickness=0,
            bd=0,
            font=self.fonts["body"],
            activestyle="none",
            yscrollcommand=lb_scroll.set,
        )
        lb_scroll.config(command=self.input_listbox.yview)
        self.input_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_listbox.bind("<<ListboxSelect>>", self.on_input_select)

        # Output Column + Selection Summary
        output_frame = ttk.Frame(col_frame, style="Card.TFrame")
        output_frame.grid(row=0, column=1, rowspan=2, sticky=tk.NSEW)

        ttk.Label(
            output_frame, text="Target Output Response:", style="CardBold.TLabel"
        ).pack(anchor=tk.W, pady=(2, 4))
        self.output_combo = ttk.Combobox(output_frame, state="readonly")
        self.output_combo.pack(fill=tk.X, pady=(0, 8))
        self.output_combo.bind("<<ComboboxSelected>>", self._on_output_selected)

        self.col_selection_hint_var = tk.StringVar(
            value="Load a dataset to populate columns.\nGoal: Minimize Target Output."
        )
        ttk.Label(
            output_frame,
            textvariable=self.col_selection_hint_var,
            style="CardMuted.TLabel",
            wraplength=190,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, fill=tk.X)

        # --- 3. Model & Fit Settings ---
        self.settings_frame = ttk.LabelFrame(
            left_pane, text="3. Model & Fit Settings", padding=(10, 8)
        )
        self.settings_frame.pack(fill=tk.X, pady=(0, 8))

        settings_row = ttk.Frame(self.settings_frame, style="Card.TFrame")
        settings_row.pack(fill=tk.X)

        ttk.Label(settings_row, text="Method:", style="CardBold.TLabel").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.method_var = tk.StringVar(value="Gaussian Process")
        self.method_combo = ttk.Combobox(
            settings_row,
            textvariable=self.method_var,
            values=rsm_backend.get_supported_methods(),
            state="readonly",
            width=18,
        )
        self.method_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.method_combo.bind("<<ComboboxSelected>>", self._on_method_change)

        ttk.Label(settings_row, text="Degree:", style="CardBold.TLabel").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.degree_var = tk.IntVar(value=2)
        self.degree_spin = ttk.Spinbox(
            settings_row, from_=0, to=10, textvariable=self.degree_var, width=4
        )
        self.degree_spin.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(settings_row, text="Test Ratio:", style="CardBold.TLabel").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.test_size_var = tk.DoubleVar(value=0.20)
        self.test_size_spin = ttk.Spinbox(
            settings_row,
            from_=0.01,
            to=0.99,
            increment=0.05,
            textvariable=self.test_size_var,
            width=5,
        )
        self.test_size_spin.pack(side=tk.LEFT)

        self.method_hint_var = tk.StringVar()
        ttk.Label(
            self.settings_frame,
            textvariable=self.method_hint_var,
            style="CardMuted.TLabel",
        ).pack(anchor=tk.W, pady=(4, 6))

        fit_action_row = ttk.Frame(self.settings_frame, style="Card.TFrame")
        fit_action_row.pack(fill=tk.X)

        self.fit_btn = ttk.Button(
            fit_action_row,
            text="▶  Fit Surrogate Model",
            style="Primary.TButton",
            command=self.fit_model,
        )
        self.fit_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.fit_status_var = tk.StringVar(value="Model not fitted yet.")
        self.fit_status_lbl = tk.Label(
            fit_action_row,
            textvariable=self.fit_status_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["small_bold"],
            anchor=tk.W,
        )
        self.fit_status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._on_method_change()
        self.degree_var.trace_add("write", lambda *args: self._check_fit_settings_staleness())
        self.test_size_var.trace_add("write", lambda *args: self._check_fit_settings_staleness())

        # --- 4. Optimization Goal & Bounds (Scrollable) ---
        self.bounds_frame = ttk.LabelFrame(
            left_pane, text="4. Optimization Goal & Bounds (Optional)", padding=(10, 6)
        )
        self.bounds_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        bounds_toolbar = ttk.Frame(self.bounds_frame, style="Card.TFrame")
        bounds_toolbar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(
            bounds_toolbar,
            text="Optimization Goal:",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.opt_goal_var = tk.StringVar(value="Minimize")
        self.opt_goal_combo = ttk.Combobox(
            bounds_toolbar,
            textvariable=self.opt_goal_var,
            values=["Minimize", "Maximize"],
            state="readonly",
            width=10,
        )
        self.opt_goal_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.opt_goal_combo.bind("<<ComboboxSelected>>", self._on_opt_goal_change)

        ttk.Button(
            bounds_toolbar,
            text="Clear",
            style="Small.TButton",
            command=self.clear_bounds_entries,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            bounds_toolbar,
            text="Fill from Data Range",
            style="Small.TButton",
            command=self.fill_bounds_from_data,
        ).pack(side=tk.RIGHT)

        bounds_canvas_wrap = ttk.Frame(self.bounds_frame, style="Card.TFrame")
        bounds_canvas_wrap.pack(fill=tk.BOTH, expand=True)

        self.bounds_canvas = tk.Canvas(
            bounds_canvas_wrap,
            height=85,
            bg=PALETTE["bg_card"],
            bd=0,
            highlightthickness=0,
        )
        bounds_scroll = ttk.Scrollbar(
            bounds_canvas_wrap, orient=tk.VERTICAL, command=self.bounds_canvas.yview
        )
        self.bounds_inner_frame = ttk.Frame(self.bounds_canvas, style="Card.TFrame")
        self.bounds_inner_frame.bind(
            "<Configure>",
            lambda e: self.bounds_canvas.configure(scrollregion=self.bounds_canvas.bbox("all")),
        )
        self._bounds_canvas_win = self.bounds_canvas.create_window(
            (0, 0), window=self.bounds_inner_frame, anchor="nw"
        )
        self.bounds_canvas.bind(
            "<Configure>",
            lambda e: self.bounds_canvas.itemconfigure(self._bounds_canvas_win, width=e.width),
        )
        self.bounds_canvas.configure(yscrollcommand=bounds_scroll.set)
        self.bounds_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bounds_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 5. Linear Constraints ---
        self.constraints_frame = ttk.LabelFrame(
            left_pane, text="5. Linear Constraints (Optional)", padding=(10, 6)
        )
        self.constraints_frame.pack(fill=tk.X, pady=(0, 8))

        c_btn_frame = ttk.Frame(self.constraints_frame, style="Card.TFrame")
        c_btn_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(
            c_btn_frame,
            text="+ Add Constraint",
            style="Small.TButton",
            command=self.add_linear_constraint,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame,
            text="Edit Selected",
            style="Small.TButton",
            command=self.edit_linear_constraint,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame,
            text="Delete Selected",
            style="Small.TButton",
            command=self.delete_linear_constraint,
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            c_btn_frame,
            text="Clear All",
            style="Danger.TButton",
            command=self.clear_linear_constraints,
        ).pack(side=tk.RIGHT)

        tree_frame = ttk.Frame(self.constraints_frame, style="Card.TFrame")
        tree_frame.pack(fill=tk.X, expand=True)

        self.constraints_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "expression", "operator", "bound"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        self.constraints_tree.heading("id", text="#")
        self.constraints_tree.heading("expression", text="Linear Combination Expression")
        self.constraints_tree.heading("operator", text="Operator")
        self.constraints_tree.heading("bound", text="Bound")

        self.constraints_tree.column("id", width=32, anchor=tk.CENTER, stretch=False)
        self.constraints_tree.column("expression", width=250, anchor=tk.W)
        self.constraints_tree.column("operator", width=65, anchor=tk.CENTER, stretch=False)
        self.constraints_tree.column("bound", width=80, anchor=tk.E, stretch=False)

        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.constraints_tree.yview
        )
        self.constraints_tree.configure(yscrollcommand=tree_scroll.set)
        self.constraints_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.constraints_tree.bind("<Double-1>", lambda event: self.edit_linear_constraint())

        # --- Action Buttons Bar ---
        run_frame = ttk.Frame(left_pane)
        run_frame.pack(fill=tk.X, pady=(2, 0))
        run_frame.columnconfigure(0, weight=3)
        run_frame.columnconfigure(1, weight=2)

        self.run_btn = ttk.Button(
            run_frame,
            text="▶  Run Optimization",
            style="Primary.TButton",
            command=self.run_optimization,
            state="disabled",
        )
        self.run_btn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))

        self.plot_config_btn = ttk.Button(
            run_frame,
            text="⚙  Configure Plot...",
            style="Secondary.TButton",
            command=self.open_plot_config,
            state="disabled",
        )
        self.plot_config_btn.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))

        # =====================================================================
        # RIGHT PANE: KPI Summary Cards + Tabbed Results, Evaluation & Report
        # =====================================================================

        # --- KPI Summary Strip ---
        kpi_strip = ttk.Frame(right_pane)
        kpi_strip.pack(fill=tk.X, pady=(0, 8))
        for col_idx in range(4):
            kpi_strip.columnconfigure(col_idx, weight=1, uniform="kpi")

        self.kpi_r2 = self._create_kpi_card(
            kpi_strip, 0, "R² FIT SCORE", "—", "Not fitted yet"
        )
        self.kpi_rmse = self._create_kpi_card(
            kpi_strip, 1, "TEST RMSE", "—", "MSE: —"
        )
        self.kpi_opt = self._create_kpi_card(
            kpi_strip, 2, "MIN OUTPUT VALUE", "—", "Target: —"
        )
        self.kpi_status = self._create_kpi_card(
            kpi_strip, 3, "MODEL & OPT STATUS", "Idle", "Fit model to begin"
        )

        # --- Results Notebook ---
        self.results_notebook = ttk.Notebook(right_pane)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Structured Tables (Optimal Solution & Constraints)
        tables_tab = ttk.Frame(self.results_notebook, style="Card.TFrame", padding=10)
        self.results_notebook.add(tables_tab, text="  Optimal Solution & Constraints  ")

        opt_lbl_frame = ttk.Frame(tables_tab, style="Card.TFrame")
        opt_lbl_frame.pack(fill=tk.X, pady=(0, 4))
        self.opt_table_hdr_var = tk.StringVar(
            value="Optimized Input Parameters (Minimizing Target Output)"
        )
        ttk.Label(
            opt_lbl_frame,
            textvariable=self.opt_table_hdr_var,
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)

        opt_tree_wrap = ttk.Frame(tables_tab, style="Card.TFrame")
        opt_tree_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.opt_params_tree = ttk.Treeview(
            opt_tree_wrap,
            columns=("param", "opt_val", "bounds", "data_range"),
            show="headings",
            height=6,
            selectmode="browse",
        )
        self.opt_params_tree.heading("param", text="Parameter")
        self.opt_params_tree.heading("opt_val", text="Optimal Value")
        self.opt_params_tree.heading("bounds", text="Applied Bounds")
        self.opt_params_tree.heading("data_range", text="Dataset [Min, Max]")

        self.opt_params_tree.column("param", width=130, anchor=tk.W)
        self.opt_params_tree.column("opt_val", width=120, anchor=tk.E)
        self.opt_params_tree.column("bounds", width=130, anchor=tk.CENTER)
        self.opt_params_tree.column("data_range", width=140, anchor=tk.CENTER)

        opt_scroll = ttk.Scrollbar(
            opt_tree_wrap, orient=tk.VERTICAL, command=self.opt_params_tree.yview
        )
        self.opt_params_tree.configure(yscrollcommand=opt_scroll.set)
        self.opt_params_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        opt_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Constraint Verification Table in Tab 1
        ver_lbl_frame = ttk.Frame(tables_tab, style="Card.TFrame")
        ver_lbl_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            ver_lbl_frame,
            text="Linear Constraint Verification at Optimal Point",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)

        ver_tree_wrap = ttk.Frame(tables_tab, style="Card.TFrame")
        ver_tree_wrap.pack(fill=tk.BOTH, expand=True)

        self.constraint_eval_tree = ttk.Treeview(
            ver_tree_wrap,
            columns=("id", "expr", "lhs", "status"),
            show="headings",
            height=4,
            selectmode="browse",
        )
        self.constraint_eval_tree.heading("id", text="#")
        self.constraint_eval_tree.heading("expr", text="Constraint Expression")
        self.constraint_eval_tree.heading("lhs", text="Evaluated LHS")
        self.constraint_eval_tree.heading("status", text="Status")

        self.constraint_eval_tree.column("id", width=35, anchor=tk.CENTER, stretch=False)
        self.constraint_eval_tree.column("expr", width=230, anchor=tk.W)
        self.constraint_eval_tree.column("lhs", width=110, anchor=tk.E)
        self.constraint_eval_tree.column("status", width=95, anchor=tk.CENTER, stretch=False)
        self.constraint_eval_tree.tag_configure("satisfied", foreground=PALETTE["success"])
        self.constraint_eval_tree.tag_configure("violated", foreground=PALETTE["danger"])

        ver_scroll = ttk.Scrollbar(
            ver_tree_wrap, orient=tk.VERTICAL, command=self.constraint_eval_tree.yview
        )
        self.constraint_eval_tree.configure(yscrollcommand=ver_scroll.set)
        self.constraint_eval_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ver_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tab 2: Full Report & Model Equation (Preserves self.results_text)
        report_tab = ttk.Frame(self.results_notebook, style="Card.TFrame", padding=10)
        self.results_notebook.add(report_tab, text="  Model Equation & Full Report  ")

        report_toolbar = ttk.Frame(report_tab, style="Card.TFrame")
        report_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            report_toolbar,
            text="Detailed Model Summary, Coefficients / Symbolic Expression & Diagnostics",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            report_toolbar,
            text="Copy Report",
            style="Small.TButton",
            command=self.copy_results_to_clipboard,
        ).pack(side=tk.RIGHT)

        text_wrap = tk.Frame(report_tab, bg=PALETTE["border"], bd=1, relief=tk.FLAT)
        text_wrap.pack(fill=tk.BOTH, expand=True)
        text_scroll = ttk.Scrollbar(text_wrap, orient=tk.VERTICAL)
        self.results_text = tk.Text(
            text_wrap,
            height=12,
            state="disabled",
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["text_main"],
            font=self.fonts["mono"],
            bd=0,
            padx=10,
            pady=8,
            wrap=tk.WORD,
            yscrollcommand=text_scroll.set,
        )
        text_scroll.config(command=self.results_text.yview)
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tab 3: Evaluate Surrogate Model at Custom Input Point
        eval_tab = ttk.Frame(self.results_notebook, style="Card.TFrame", padding=10)
        self.results_notebook.add(eval_tab, text="  Evaluate Model  ")

        eval_toolbar = ttk.Frame(eval_tab, style="Card.TFrame")
        eval_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            eval_toolbar,
            text="Specify Input Parameter Values:",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)

        ttk.Button(
            eval_toolbar,
            text="Clear",
            style="Small.TButton",
            command=self.clear_eval_entries,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            eval_toolbar,
            text="Fill with Data Mean",
            style="Small.TButton",
            command=self.fill_eval_from_mean,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            eval_toolbar,
            text="Fill from Optimal Solution",
            style="Small.TButton",
            command=self.fill_eval_from_optimal,
        ).pack(side=tk.RIGHT)

        # Scrollable Parameter Inputs for Point Evaluation
        eval_inputs_wrap = ttk.Frame(eval_tab, style="Card.TFrame")
        eval_inputs_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.eval_inputs_canvas = tk.Canvas(
            eval_inputs_wrap,
            height=115,
            bg=PALETTE["bg_card"],
            bd=0,
            highlightthickness=0,
        )
        eval_inputs_scroll = ttk.Scrollbar(
            eval_inputs_wrap, orient=tk.VERTICAL, command=self.eval_inputs_canvas.yview
        )
        self.eval_inputs_inner_frame = ttk.Frame(self.eval_inputs_canvas, style="Card.TFrame")
        self.eval_inputs_inner_frame.bind(
            "<Configure>",
            lambda e: self.eval_inputs_canvas.configure(
                scrollregion=self.eval_inputs_canvas.bbox("all")
            ),
        )
        self._eval_canvas_win = self.eval_inputs_canvas.create_window(
            (0, 0), window=self.eval_inputs_inner_frame, anchor="nw"
        )
        self.eval_inputs_canvas.bind(
            "<Configure>",
            lambda e: self.eval_inputs_canvas.itemconfigure(
                self._eval_canvas_win, width=e.width
            ),
        )
        self.eval_inputs_canvas.configure(yscrollcommand=eval_inputs_scroll.set)
        self.eval_inputs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        eval_inputs_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Evaluation Action & Predicted Output Banner
        eval_result_bar = tk.Frame(
            eval_tab,
            bg=PALETTE["bg_subtle"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        eval_result_bar.pack(fill=tk.X, pady=(0, 8))

        self.eval_run_btn = ttk.Button(
            eval_result_bar,
            text="▶  Evaluate Output",
            style="Primary.TButton",
            command=self.evaluate_custom_point,
            state="disabled",
        )
        self.eval_run_btn.pack(side=tk.LEFT, padx=(0, 14))

        eval_readout_box = tk.Frame(eval_result_bar, bg=PALETTE["bg_subtle"])
        eval_readout_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.eval_pred_var = tk.StringVar(value="Predicted Output:  —")
        tk.Label(
            eval_readout_box,
            textvariable=self.eval_pred_var,
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["accent"],
            font=self.fonts["title"],
            anchor=tk.W,
        ).pack(fill=tk.X)

        self.eval_unc_var = tk.StringVar(
            value="Fit a surrogate model to evaluate predictions at custom parameter combinations."
        )
        tk.Label(
            eval_readout_box,
            textvariable=self.eval_unc_var,
            bg=PALETTE["bg_subtle"],
            fg=PALETTE["text_secondary"],
            font=self.fonts["small"],
            anchor=tk.W,
        ).pack(fill=tk.X)

        # Evaluation History Table
        hist_hdr_frame = ttk.Frame(eval_tab, style="Card.TFrame")
        hist_hdr_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            hist_hdr_frame,
            text="Evaluated Points History (Double-click a row to reload its inputs)",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Button(
            hist_hdr_frame,
            text="Clear History",
            style="Danger.TButton",
            command=self.clear_eval_history,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            hist_hdr_frame,
            text="Copy History",
            style="Small.TButton",
            command=self.copy_eval_history,
        ).pack(side=tk.RIGHT)

        hist_tree_wrap = ttk.Frame(eval_tab, style="Card.TFrame")
        hist_tree_wrap.pack(fill=tk.BOTH, expand=True)

        self.eval_history_tree = ttk.Treeview(
            hist_tree_wrap,
            columns=("id", "inputs", "predicted", "uncertainty"),
            show="headings",
            height=4,
            selectmode="browse",
        )
        self.eval_history_tree.heading("id", text="#")
        self.eval_history_tree.heading("inputs", text="Input Parameter Combination")
        self.eval_history_tree.heading("predicted", text="Predicted Output")
        self.eval_history_tree.heading("uncertainty", text="Std Dev (±σ)")

        self.eval_history_tree.column("id", width=35, anchor=tk.CENTER, stretch=False)
        self.eval_history_tree.column("inputs", width=260, anchor=tk.W)
        self.eval_history_tree.column("predicted", width=115, anchor=tk.E)
        self.eval_history_tree.column("uncertainty", width=110, anchor=tk.E)

        hist_scroll = ttk.Scrollbar(
            hist_tree_wrap, orient=tk.VERTICAL, command=self.eval_history_tree.yview
        )
        self.eval_history_tree.configure(yscrollcommand=hist_scroll.set)
        self.eval_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.eval_history_tree.bind("<Double-1>", self._on_eval_history_double_click)

        # Initialize empty bounds & evaluation inputs hints
        self.on_input_select()

        # =====================================================================
        # Bottom Status Bar
        # =====================================================================
        status_bar = tk.Frame(
            self,
            bg=PALETTE["bg_card"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=12,
            pady=4,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(
            value="Ready — Browse and select a CSV or Excel dataset to begin."
        )
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_secondary"],
            font=self.fonts["small"],
            anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # =========================================================================
    # Helper UI Builders & State Callbacks
    # =========================================================================

    def _create_kpi_card(self, parent, col_idx, title, initial_val, initial_sub):
        padx = (0, 6) if col_idx < 3 else (0, 0)
        card = tk.Frame(
            parent,
            bg=PALETTE["bg_card"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        card.grid(row=0, column=col_idx, sticky=tk.NSEW, padx=padx)

        accent_bar = tk.Frame(card, bg=PALETTE["accent"], height=3)
        accent_bar.pack(fill=tk.X, side=tk.TOP)

        body = tk.Frame(card, bg=PALETTE["bg_card"], padx=10, pady=6)
        body.pack(fill=tk.BOTH, expand=True)

        title_var = tk.StringVar(value=title)
        lbl_title = tk.Label(
            body,
            textvariable=title_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["kpi_label"],
            anchor=tk.W,
        )
        lbl_title.pack(fill=tk.X)

        val_var = tk.StringVar(value=initial_val)
        lbl_val = tk.Label(
            body,
            textvariable=val_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_main"],
            font=self.fonts["kpi_value"],
            anchor=tk.W,
        )
        lbl_val.pack(fill=tk.X, pady=(1, 1))

        sub_var = tk.StringVar(value=initial_sub)
        lbl_sub = tk.Label(
            body,
            textvariable=sub_var,
            bg=PALETTE["bg_card"],
            fg=PALETTE["text_muted"],
            font=self.fonts["small"],
            anchor=tk.W,
        )
        lbl_sub.pack(fill=tk.X)

        return {
            "accent": accent_bar,
            "title_var": title_var,
            "val_var": val_var,
            "sub_var": sub_var,
            "val_lbl": lbl_val,
        }

    def _get_current_fit_signature(self):
        if self.df is None:
            return None
        selected_indices = self.input_listbox.curselection()
        input_cols = tuple(self.input_listbox.get(i) for i in selected_indices)
        output_col = self.output_combo.get()
        method = self.method_var.get()
        try:
            degree = int(self.degree_var.get()) if method != "Genetic Programming" else 0
        except (tk.TclError, ValueError):
            degree = None
        try:
            test_size = round(float(self.test_size_var.get()), 6)
        except (tk.TclError, ValueError):
            test_size = None
        return (id(self.df), input_cols, output_col, method, degree, test_size)

    def _check_fit_settings_staleness(self):
        if self.result is None or self.fitted_model_signature is None:
            return
        curr_sig = self._get_current_fit_signature()
        if curr_sig != self.fitted_model_signature:
            self.fit_status_var.set(
                f"⚠ Settings changed (Active: {self.result.method}, R²={self.result.R_sq:.4f}) — click Fit to update."
            )
            self.fit_status_lbl.config(fg=PALETTE["warning"])
        else:
            self.fit_status_var.set(
                f"✓ Fitted: {self.result.method} (R² = {self.result.R_sq:.4f})"
            )
            self.fit_status_lbl.config(fg=PALETTE["success"])

    def _invalidate_fitted_model(self, reason_msg="Model not fitted yet."):
        self.result = None
        self.current_input_cols = None
        self.current_output_col = None
        self.fitted_model_signature = None
        self.last_opt_report_text = ""
        self.opt_params_dict = {}

        if hasattr(self, "fit_status_var"):
            self.fit_status_var.set(reason_msg)
            self.fit_status_lbl.config(fg=PALETTE["text_muted"])
        if hasattr(self, "run_btn"):
            self.run_btn.config(state="disabled")
        if hasattr(self, "plot_config_btn"):
            self.plot_config_btn.config(state="disabled")
        if hasattr(self, "eval_run_btn"):
            self.eval_run_btn.config(state="disabled")
        if hasattr(self, "eval_pred_var"):
            self.eval_pred_var.set("Predicted Output:  —")
            self.eval_unc_var.set(
                "Fit a surrogate model to evaluate predictions at custom parameter combinations."
            )
        if hasattr(self, "kpi_r2"):
            self.kpi_r2["val_var"].set("—")
            self.kpi_r2["sub_var"].set("Not fitted yet")
            self.kpi_r2["accent"].config(bg=PALETTE["accent"])
            self.kpi_rmse["val_var"].set("—")
            self.kpi_rmse["sub_var"].set("MSE: —")
            self.kpi_opt["val_var"].set("—")
            self.kpi_opt["sub_var"].set("Target: —")
            self.kpi_status["val_var"].set("Idle")
            self.kpi_status["sub_var"].set("Fit model to begin")
            self.kpi_status["accent"].config(bg=PALETTE["accent"])

    def _on_method_change(self, event=None):
        method = self.method_var.get()
        if method == "Genetic Programming":
            self.degree_spin.config(state="disabled")
            self.method_hint_var.set(
                "Symbolic regression via gplearn — discovers closed-form equations (polynomial degree N/A)."
            )
        elif method == "RidgeCV":
            self.degree_spin.config(state="normal", from_=1, to=10)
            try:
                if self.degree_var.get() < 1:
                    self.degree_var.set(2)
            except tk.TclError:
                self.degree_var.set(2)
            self.method_hint_var.set(
                "Cross-validated L2 polynomial regression — extracts unscaled polynomial coefficients."
            )
        else:
            self.degree_spin.config(state="normal", from_=0, to=10)
            self.method_hint_var.set(
                "Kriging model — Degree 0: Ordinary Kriging | Degree ≥ 1: Universal Kriging + uncertainty."
            )
        self._check_fit_settings_staleness()

    def _on_opt_goal_change(self, event=None):
        goal = self.opt_goal_var.get() if hasattr(self, "opt_goal_var") else "Minimize"
        is_max = goal == "Maximize"
        if hasattr(self, "kpi_opt"):
            self.kpi_opt["title_var"].set("MAX OUTPUT VALUE" if is_max else "MIN OUTPUT VALUE")
        if hasattr(self, "opt_table_hdr_var"):
            verb = "Maximizing" if is_max else "Minimizing"
            self.opt_table_hdr_var.set(f"Optimized Input Parameters ({verb} Target Output)")
        self._update_column_selection_hint()

    def _on_output_selected(self, event=None):
        output_col = self.output_combo.get()
        selected_indices = list(self.input_listbox.curselection())
        changed = False
        for idx in selected_indices:
            if self.input_listbox.get(idx) == output_col:
                self.input_listbox.selection_clear(idx)
                changed = True
        if changed:
            self.on_input_select()
        else:
            if self.result is not None and output_col != self.current_output_col:
                self._invalidate_fitted_model("Target output changed — click 'Fit Surrogate Model'.")
            self._update_column_selection_hint()

    def _update_column_selection_hint(self):
        n_in = len(self.input_listbox.curselection())
        out_col = self.output_combo.get()
        goal = self.opt_goal_var.get() if hasattr(self, "opt_goal_var") else "Minimize"
        if self.df is None:
            self.col_selection_hint_var.set(
                f"Load a dataset to populate columns.\nGoal: {goal} Target Output."
            )
        else:
            out_txt = f"'{out_col}'" if out_col else "None selected"
            self.col_selection_hint_var.set(
                f"Selected: {n_in} input factor(s)\nTarget: {out_txt} ({goal})"
            )

    def select_all_inputs(self):
        if self.df is None:
            return
        output_col = self.output_combo.get()
        self.input_listbox.selection_clear(0, tk.END)
        for i in range(self.input_listbox.size()):
            if self.input_listbox.get(i) != output_col:
                self.input_listbox.selection_set(i)
        self.on_input_select()

    def clear_input_selection(self):
        self.input_listbox.selection_clear(0, tk.END)
        self.on_input_select()

    def fill_bounds_from_data(self):
        if self.df is None or not self.bound_entries:
            return
        for col_name, (min_var, max_var) in self.bound_entries.items():
            if col_name in self.df.columns:
                col_series = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
                if not col_series.empty:
                    min_var.set(f"{float(col_series.min()):.6g}")
                    max_var.set(f"{float(col_series.max()):.6g}")
        self.status_var.set("Populated optimization bounds from dataset [min, max] ranges.")

    def clear_bounds_entries(self):
        for min_var, max_var in self.bound_entries.values():
            min_var.set("")
            max_var.set("")
        self.status_var.set("Cleared optimization bounds.")

    def copy_results_to_clipboard(self):
        content = self.results_text.get("1.0", tk.END).strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_var.set("Copied model report to clipboard.")

    # =========================================================================
    # Surrogate Model Point Evaluation Helpers
    # =========================================================================

    def _get_col_mean_str(self, col_name):
        if self.df is None or col_name not in self.df.columns:
            return "0"
        series = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
        if series.empty:
            return "0"
        return f"{float(series.mean()):.6g}"

    def fill_eval_from_optimal(self):
        if not self.eval_entries:
            return
        if not self.opt_params_dict:
            messagebox.showinfo(
                "Info",
                "Run optimization first to populate optimal parameter values, or use 'Fill with Data Mean'.",
            )
            return
        for col_name, var in self.eval_entries.items():
            if col_name in self.opt_params_dict:
                var.set(f"{self.opt_params_dict[col_name]:.6g}")
        self.status_var.set("Populated evaluation inputs from the latest optimal solution.")

    def fill_eval_from_mean(self):
        if not self.eval_entries:
            return
        for col_name, var in self.eval_entries.items():
            var.set(self._get_col_mean_str(col_name))
        self.status_var.set("Populated evaluation inputs with dataset column means.")

    def clear_eval_entries(self):
        for var in self.eval_entries.values():
            var.set("")
        self.status_var.set("Cleared evaluation input fields.")

    def clear_eval_history(self):
        self.eval_history.clear()
        for item in self.eval_history_tree.get_children():
            self.eval_history_tree.delete(item)
        self.status_var.set("Cleared evaluation history.")

    def copy_eval_history(self):
        if not self.eval_history:
            return
        lines = ["#\tInputs\tPredicted Output\tStd Dev"]
        for rec in self.eval_history:
            lines.append(
                f"{rec['id']}\t{rec['inputs_str']}\t{rec['pred_str']}\t{rec['std_str']}"
            )
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.status_var.set("Copied evaluation history to clipboard.")

    def _on_eval_history_double_click(self, event=None):
        sel = self.eval_history_tree.selection()
        if not sel:
            return
        item_id = sel[0]
        idx = int(self.eval_history_tree.item(item_id, "values")[0]) - 1
        if 0 <= idx < len(self.eval_history):
            params_dict = self.eval_history[idx]["params_dict"]
            for col, val in params_dict.items():
                if col in self.eval_entries:
                    self.eval_entries[col].set(f"{val:.6g}")
            self.status_var.set(f"Reloaded evaluation point #{idx + 1} into input fields.")

    def evaluate_custom_point(self):
        if self.result is None or not self.current_input_cols:
            messagebox.showwarning(
                "Warning", "Please fit the surrogate model first before evaluating points."
            )
            return

        param_vals = []
        params_dict = {}
        for col in self.current_input_cols:
            var = self.eval_entries.get(col)
            txt = var.get().strip() if var is not None else ""
            if not txt:
                messagebox.showerror(
                    "Error", f"Please enter a numeric value for input parameter '{col}'."
                )
                return
            try:
                val = float(txt)
            except ValueError:
                messagebox.showerror(
                    "Error", f"Invalid numeric value for '{col}': '{txt}'."
                )
                return
            param_vals.append(val)
            params_dict[col] = val

        try:
            y_val, std_val = self.result.evaluate_point(param_vals, return_std=True)
            out_col = self.current_output_col or self.output_combo.get() or "Output"

            self.eval_pred_var.set(f"Predicted {out_col}:  {y_val:.6g}")
            if std_val is not None:
                ci_low = y_val - 1.96 * std_val
                ci_high = y_val + 1.96 * std_val
                self.eval_unc_var.set(
                    f"Predictive Std Dev (±1σ): ±{std_val:.5g}   |   95% CI: [{ci_low:.5g}, {ci_high:.5g}]"
                )
                std_str = f"±{std_val:.5g}"
            else:
                self.eval_unc_var.set(
                    f"Model: {self.result.method} (Deterministic prediction — uncertainty N/A)"
                )
                std_str = "—"

            inputs_str = ", ".join(f"{c}={v:.5g}" for c, v in params_dict.items())
            pred_str = f"{y_val:.6g}"
            rec_id = len(self.eval_history) + 1
            record = {
                "id": rec_id,
                "params_dict": params_dict,
                "inputs_str": inputs_str,
                "pred_val": y_val,
                "std_val": std_val,
                "pred_str": pred_str,
                "std_str": std_str,
            }
            self.eval_history.append(record)
            self.eval_history_tree.insert(
                "",
                tk.END,
                values=(rec_id, inputs_str, pred_str, std_str),
            )
            self.status_var.set(
                f"Evaluated {self.result.method} at ({inputs_str}) → {out_col} = {y_val:.6g}."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to evaluate surrogate model:\n{e!s}")

    # =========================================================================
    # Linear Constraints Management
    # =========================================================================

    def add_linear_constraint(self):
        selected_indices = self.input_listbox.curselection()
        input_cols = [self.input_listbox.get(i) for i in selected_indices]
        if not input_cols:
            messagebox.showwarning("Warning", "Please select input columns first before adding constraints.")
            return

        def save_callback(cdata):
            self.linear_constraints.append(cdata)
            self.refresh_constraints_tree()

        LinearConstraintDialog(self, input_cols, on_save_callback=save_callback)

    def edit_linear_constraint(self):
        selected_item = self.constraints_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a constraint from the list to edit.")
            return

        item_id = selected_item[0]
        idx = int(self.constraints_tree.item(item_id, "values")[0]) - 1
        if 0 <= idx < len(self.linear_constraints):
            selected_indices = self.input_listbox.curselection()
            input_cols = [self.input_listbox.get(i) for i in selected_indices]

            def save_callback(cdata):
                self.linear_constraints[idx] = cdata
                self.refresh_constraints_tree()

            LinearConstraintDialog(
                self,
                input_cols,
                existing_constraint=self.linear_constraints[idx],
                on_save_callback=save_callback
            )

    def delete_linear_constraint(self):
        selected_item = self.constraints_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a constraint from the list to delete.")
            return

        item_id = selected_item[0]
        idx = int(self.constraints_tree.item(item_id, "values")[0]) - 1
        if 0 <= idx < len(self.linear_constraints):
            del self.linear_constraints[idx]
            self.refresh_constraints_tree()

    def clear_linear_constraints(self):
        if not self.linear_constraints:
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to remove all linear constraints?"):
            self.linear_constraints.clear()
            self.refresh_constraints_tree()

    def refresh_constraints_tree(self):
        for item in self.constraints_tree.get_children():
            self.constraints_tree.delete(item)

        for i, c in enumerate(self.linear_constraints, 1):
            self.constraints_tree.insert(
                "",
                tk.END,
                values=(i, c["expression_str"], c["operator"], f"{c['bound']:g}")
            )

    # =========================================================================
    # Data Loading & Variable Selection
    # =========================================================================

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*"),
            ]
        )
        if filepath:
            self.file_path_var.set(filepath)
            # Automatically load data upon selecting a file via Browse
            self.load_data(show_popup=False)

    def load_data(self, show_popup=False):
        filepath = self.file_path_var.get()
        if not filepath:
            messagebox.showwarning("Warning", "Please select a file first.")
            return

        try:
            if filepath.lower().endswith(".csv"):
                self.df = pd.read_csv(filepath)
            else:
                self.df = pd.read_excel(filepath)

            columns = list(self.df.columns)

            # Update Listbox and Combobox
            self.input_listbox.delete(0, tk.END)
            for col in columns:
                self.input_listbox.insert(tk.END, col)

            self.output_combo["values"] = columns
            self.output_combo.set("")

            # Clear bounds, evaluation history, fitted model, and linear constraints
            self.linear_constraints.clear()
            self.refresh_constraints_tree()
            self.clear_eval_history()
            self._invalidate_fitted_model("Dataset loaded — select columns and click 'Fit Surrogate Model'.")
            self.on_input_select()

            filename = Path(filepath).name
            self.dataset_badge_var.set(
                f"{filename}  •  {len(self.df)} rows × {len(columns)} cols"
            )
            self.dataset_badge_lbl.config(bg="#1E3A8A", fg="#DBEAFE")
            self.status_var.set(
                f"Loaded '{filename}' ({len(self.df)} rows, {len(columns)} columns). Select input factors and target output."
            )

            if show_popup:
                messagebox.showinfo(
                    "Success",
                    f"Loaded data with {len(self.df)} rows and {len(columns)} columns.",
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e!s}")

    def _get_col_range_str(self, col_name):
        if self.df is None or col_name not in self.df.columns:
            return "—"
        series = pd.to_numeric(self.df[col_name], errors="coerce").dropna()
        if series.empty:
            return "—"
        return f"[{float(series.min()):.4g}, {float(series.max()):.4g}]"

    def on_input_select(self, event=None):
        selected_indices = self.input_listbox.curselection()
        current_cols = [self.input_listbox.get(idx) for idx in selected_indices]

        prev_cols = getattr(self, "previous_input_cols", [])
        if current_cols != prev_cols and self.result is not None:
            self._invalidate_fitted_model("Input factors changed — click 'Fit Surrogate Model'.")

        # Reset constraints if the selected input columns have changed
        if self.linear_constraints and set(current_cols) != set(prev_cols):
            self.linear_constraints.clear()
            self.refresh_constraints_tree()
        self.previous_input_cols = current_cols

        # Preserve any already-entered bounds for columns that remain selected
        existing_bounds = {
            k: (v[0].get(), v[1].get()) for k, v in self.bound_entries.items()
        }
        existing_eval = {
            k: v.get() for k, v in self.eval_entries.items()
        }

        # Clear existing bounds widgets
        for widget in self.bounds_inner_frame.winfo_children():
            widget.destroy()
        self.bound_entries = {}

        # Clear existing evaluation input widgets
        if hasattr(self, "eval_inputs_inner_frame"):
            for widget in self.eval_inputs_inner_frame.winfo_children():
                widget.destroy()
        self.eval_entries = {}

        self._update_column_selection_hint()

        if not selected_indices:
            ttk.Label(
                self.bounds_inner_frame,
                text="Select input factors above to configure optional min/max bounds.",
                style="CardMuted.TLabel",
            ).pack(anchor=tk.W, padx=4, pady=12)
            if hasattr(self, "eval_inputs_inner_frame"):
                ttk.Label(
                    self.eval_inputs_inner_frame,
                    text="Select input factors and fit the model to evaluate outputs at custom points.",
                    style="CardMuted.TLabel",
                ).pack(anchor=tk.W, padx=4, pady=12)
            return

        self.bounds_inner_frame.columnconfigure(0, weight=2)
        self.bounds_inner_frame.columnconfigure(1, weight=2)
        self.bounds_inner_frame.columnconfigure(2, weight=2)
        self.bounds_inner_frame.columnconfigure(3, weight=2)

        # Headers for Bounds
        ttk.Label(self.bounds_inner_frame, text="Parameter", style="CardBold.TLabel").grid(
            row=0, column=0, padx=4, pady=(0, 4), sticky=tk.W
        )
        ttk.Label(self.bounds_inner_frame, text="Data [Min, Max]", style="CardBold.TLabel").grid(
            row=0, column=1, padx=4, pady=(0, 4), sticky=tk.W
        )
        ttk.Label(self.bounds_inner_frame, text="Min Bound", style="CardBold.TLabel").grid(
            row=0, column=2, padx=4, pady=(0, 4), sticky=tk.W
        )
        ttk.Label(self.bounds_inner_frame, text="Max Bound", style="CardBold.TLabel").grid(
            row=0, column=3, padx=4, pady=(0, 4), sticky=tk.W
        )

        # Headers for Evaluation Inputs
        if hasattr(self, "eval_inputs_inner_frame"):
            self.eval_inputs_inner_frame.columnconfigure(0, weight=2)
            self.eval_inputs_inner_frame.columnconfigure(1, weight=2)
            self.eval_inputs_inner_frame.columnconfigure(2, weight=3)
            ttk.Label(self.eval_inputs_inner_frame, text="Parameter", style="CardBold.TLabel").grid(
                row=0, column=0, padx=4, pady=(0, 4), sticky=tk.W
            )
            ttk.Label(self.eval_inputs_inner_frame, text="Dataset [Min, Max]", style="CardBold.TLabel").grid(
                row=0, column=1, padx=4, pady=(0, 4), sticky=tk.W
            )
            ttk.Label(self.eval_inputs_inner_frame, text="Evaluation Value", style="CardBold.TLabel").grid(
                row=0, column=2, padx=4, pady=(0, 4), sticky=tk.W
            )

        for i, idx in enumerate(selected_indices):
            col_name = self.input_listbox.get(idx)
            range_str = self._get_col_range_str(col_name)

            ttk.Label(self.bounds_inner_frame, text=col_name, style="Card.TLabel").grid(
                row=i + 1, column=0, padx=4, pady=2, sticky=tk.W
            )
            ttk.Label(
                self.bounds_inner_frame,
                text=range_str,
                style="CardMuted.TLabel",
            ).grid(row=i + 1, column=1, padx=4, pady=2, sticky=tk.W)

            prev_min, prev_max = existing_bounds.get(col_name, ("", ""))
            min_var = tk.StringVar(value=prev_min)
            max_var = tk.StringVar(value=prev_max)

            ttk.Entry(self.bounds_inner_frame, textvariable=min_var, width=11).grid(
                row=i + 1, column=2, padx=4, pady=2, sticky=tk.EW
            )
            ttk.Entry(self.bounds_inner_frame, textvariable=max_var, width=11).grid(
                row=i + 1, column=3, padx=4, pady=2, sticky=tk.EW
            )

            self.bound_entries[col_name] = (min_var, max_var)

            if hasattr(self, "eval_inputs_inner_frame"):
                ttk.Label(self.eval_inputs_inner_frame, text=col_name, style="Card.TLabel").grid(
                    row=i + 1, column=0, padx=4, pady=2, sticky=tk.W
                )
                ttk.Label(
                    self.eval_inputs_inner_frame,
                    text=range_str,
                    style="CardMuted.TLabel",
                ).grid(row=i + 1, column=1, padx=4, pady=2, sticky=tk.W)

                default_eval = existing_eval.get(col_name, self._get_col_mean_str(col_name))
                eval_var = tk.StringVar(value=default_eval)
                eval_entry = ttk.Entry(self.eval_inputs_inner_frame, textvariable=eval_var, width=16)
                eval_entry.grid(row=i + 1, column=2, padx=4, pady=2, sticky=tk.EW)
                eval_entry.bind("<Return>", lambda e: self.evaluate_custom_point())
                self.eval_entries[col_name] = eval_var

    # =========================================================================
    # Model Fitting & Optimization Execution (Decoupled)
    # =========================================================================

    def _render_full_report(self):
        """
        Render the combined Surrogate Model Fit Report and (if available) Optimization Report
        into Tab 2 (self.results_text).
        """
        self.results_text.config(state="normal")
        self.results_text.delete(1.0, tk.END)

        if self.result is None or not self.current_input_cols:
            self.results_text.config(state="disabled")
            return

        result = self.result
        input_cols = self.current_input_cols
        output_col = self.current_output_col or self.output_combo.get()

        self.results_text.insert(tk.END, "=== Surrogate Model Fit Summary ===\n\n")
        self.results_text.insert(tk.END, f"Target Output Variable: {output_col}\n")
        self.results_text.insert(tk.END, f"Input Factors ({len(input_cols)}): {', '.join(input_cols)}\n")
        self.results_text.insert(tk.END, f"Regression Method: {result.method}\n")
        self.results_text.insert(
            tk.END, f"Coefficient of Determination (R²): {result.R_sq:.4f}\n"
        )
        self.results_text.insert(
            tk.END, f"Mean Squared Error (MSE): {result.MSE:.6f}\n"
        )
        self.results_text.insert(
            tk.END, f"Root Mean Squared Error (RMSE): {result.RMSE:.6f}\n\n"
        )

        # Display Coefficients if available (e.g. for RidgeCV)
        if result.coeffs is not None and result.intercept is not None:
            self.results_text.insert(tk.END, "Model Coefficients:\n")
            self.results_text.insert(tk.END, f"  - Intercept: {result.intercept:.6f}\n")
            term_strings = rsm_backend.generate_term_strings(input_cols, result.model)
            for term, coeff in zip(term_strings, result.coeffs):
                self.results_text.insert(tk.END, f"  - {term}: {coeff:.6f}\n")
            self.results_text.insert(tk.END, "\n")

        # Display mathematical expression if available (e.g. for Genetic Programming)
        if getattr(result, "expression_text", None):
            self.results_text.insert(tk.END, f"{result.expression_text}\n\n")

        if self.last_opt_report_text:
            self.results_text.insert(tk.END, self.last_opt_report_text)

        self.results_text.config(state="disabled")

    def fit_model(self):
        """
        Step 3 Action: Fit the surrogate model on the selected dataset and columns without running optimization.
        """
        if self.df is None:
            messagebox.showwarning("Warning", "Please load data first.")
            return False

        selected_indices = self.input_listbox.curselection()
        input_cols = [self.input_listbox.get(i) for i in selected_indices]
        output_col = self.output_combo.get()

        if not input_cols:
            messagebox.showwarning(
                "Warning", "Please select at least one input column."
            )
            return False
        if not output_col:
            messagebox.showwarning("Warning", "Please select an output column.")
            return False
        if output_col in input_cols:
            messagebox.showwarning(
                "Warning", "Output column cannot be in the input columns."
            )
            return False

        try:
            degree = self.degree_var.get()
            test_size = self.test_size_var.get()
            method = self.method_var.get()

            if method == "RidgeCV" and degree < 1:
                messagebox.showerror("Error", "Polynomial degree must be at least 1 for RidgeCV.")
                return False

            self.status_var.set(f"Fitting {method} surrogate model...")
            self.fit_status_var.set(f"Fitting {method}...")
            self.fit_status_lbl.config(fg=PALETTE["accent"])
            self.update_idletasks()

            result = rsm_backend.rsm_fromDF(
                self.df,
                input_cols,
                output_col,
                degree_fit=degree,
                test_size=test_size,
                method=method,
            )

            self.result = result
            self.current_input_cols = input_cols
            self.current_output_col = output_col
            self.fitted_model_signature = self._get_current_fit_signature()
            self.last_opt_report_text = ""
            self.opt_params_dict = {}

            # Update Fit KPIs
            self.kpi_r2["val_var"].set(f"{result.R_sq:.4f}")
            self.kpi_r2["sub_var"].set(f"Method: {result.method}")
            self.kpi_r2["accent"].config(
                bg=PALETTE["success"]
                if result.R_sq >= 0.8
                else (PALETTE["warning"] if result.R_sq >= 0.5 else PALETTE["danger"])
            )

            self.kpi_rmse["val_var"].set(f"{result.RMSE:.5g}")
            self.kpi_rmse["sub_var"].set(f"MSE: {result.MSE:.5g}")

            # Reset Optimization KPIs & tables until optimization is run on this model
            self._on_opt_goal_change()
            self.kpi_opt["val_var"].set("—")
            self.kpi_opt["sub_var"].set(f"Target: {output_col}")

            self.kpi_status["val_var"].set("Model Fitted")
            self.kpi_status["sub_var"].set("Ready to optimize / evaluate")
            self.kpi_status["accent"].config(bg=PALETTE["accent"])

            for item in self.opt_params_tree.get_children():
                self.opt_params_tree.delete(item)
            for item in self.constraint_eval_tree.get_children():
                self.constraint_eval_tree.delete(item)

            # Update Fit status indicator & enable downstream buttons
            self.fit_status_var.set(
                f"✓ Fitted: {result.method} (R² = {result.R_sq:.4f})"
            )
            self.fit_status_lbl.config(fg=PALETTE["success"])

            self.run_btn.config(state="normal")
            self.plot_config_btn.config(state="normal")
            self.eval_run_btn.config(state="normal")

            self.eval_pred_var.set(f"Predicted {output_col}:  —")
            if result.supports_uncertainty:
                self.eval_unc_var.set(
                    f"Ready — {result.method} supports predictive uncertainty (±1σ & 95% CI)."
                )
            else:
                self.eval_unc_var.set(
                    f"Ready — Enter parameter values above and click 'Evaluate Output'."
                )

            self._render_full_report()
            self.status_var.set(
                f"Model fit complete — {result.method} (R² = {result.R_sq:.4f}, RMSE = {result.RMSE:.5g}). Ready for optimization, evaluation, or plotting."
            )
            return True

        except Exception as e:
            self.status_var.set("Model fitting failed — check error dialog.")
            self.fit_status_var.set("Fit failed.")
            self.fit_status_lbl.config(fg=PALETTE["danger"])
            messagebox.showerror(
                "Error", f"An error occurred while fitting the surrogate model:\n{e!s}"
            )
            return False

    def run_optimization(self):
        """
        Run constrained minimization or maximization using the already-fitted surrogate model (self.result)
        without re-fitting the model.
        """
        if self.df is None:
            messagebox.showwarning("Warning", "Please load data first.")
            return

        if self.result is None or not self.current_input_cols:
            messagebox.showwarning(
                "Warning",
                "Please fit the surrogate model first by clicking '▶ Fit Surrogate Model'.",
            )
            return

        input_cols = self.current_input_cols
        output_col = self.current_output_col or self.output_combo.get()
        goal = self.opt_goal_var.get()
        is_maximize = goal == "Maximize"

        bounds = []
        bounds_display = {}
        for col in input_cols:
            min_str, max_str = self.bound_entries[col]

            min_val = None
            if min_str.get().strip():
                try:
                    min_val = float(min_str.get().strip())
                except ValueError:
                    messagebox.showerror("Error", f"Invalid minimum bound for {col}")
                    return

            max_val = None
            if max_str.get().strip():
                try:
                    max_val = float(max_str.get().strip())
                except ValueError:
                    messagebox.showerror("Error", f"Invalid maximum bound for {col}")
                    return

            if min_val is not None and max_val is not None and min_val > max_val:
                messagebox.showerror(
                    "Error", f"Minimum bound cannot exceed maximum bound for '{col}'."
                )
                return

            bounds.append((min_val, max_val))
            b_min_txt = f"{min_val:g}" if min_val is not None else "-∞"
            b_max_txt = f"{max_val:g}" if max_val is not None else "+∞"
            bounds_display[col] = (
                "Unconstrained"
                if (min_val is None and max_val is None)
                else f"[{b_min_txt}, {b_max_txt}]"
            )

        # Check if all bounds are (None, None), scipy minimize sometimes prefers None instead of list of (None, None)
        if all(b == (None, None) for b in bounds):
            bounds = None

        # Build scipy.optimize.LinearConstraint if constraints are defined
        scipy_constraints = None
        if self.linear_constraints:
            A_matrix = []
            lb_vec = []
            ub_vec = []
            for c in self.linear_constraints:
                row = [c["coeffs"].get(col, 0.0) for col in input_cols]
                A_matrix.append(row)
                op = c["operator"]
                b = c["bound"]
                if op == "<=":
                    lb_vec.append(-np.inf)
                    ub_vec.append(b)
                elif op == ">=":
                    lb_vec.append(b)
                    ub_vec.append(np.inf)
                elif op == "==":
                    lb_vec.append(b)
                    ub_vec.append(b)
            scipy_constraints = LinearConstraint(np.array(A_matrix), np.array(lb_vec), np.array(ub_vec))

        try:
            result = self.result
            self.status_var.set(
                f"Running constrained {'maximization' if is_maximize else 'minimization'} on fitted {result.method} model..."
            )
            self.update_idletasks()

            # Compute a sensible initial guess within bounds or dataset means
            initial_guess = []
            for idx, col in enumerate(input_cols):
                col_mean = 0.0
                if col in self.df.columns:
                    s = pd.to_numeric(self.df[col], errors="coerce").dropna()
                    if not s.empty:
                        col_mean = float(s.mean())
                if bounds is not None:
                    b_lo, b_hi = bounds[idx]
                    if b_lo is not None and b_hi is not None:
                        col_mean = 0.5 * (b_lo + b_hi)
                    elif b_lo is not None and col_mean < b_lo:
                        col_mean = b_lo
                    elif b_hi is not None and col_mean > b_hi:
                        col_mean = b_hi
                initial_guess.append(col_mean)
            initial_guess = np.array(initial_guess, dtype=float)

            opt_params, opt_val = result.optimize(
                initial_guess=initial_guess,
                bounds=bounds,
                constraints=scipy_constraints,
                maximize=is_maximize,
            )
            if hasattr(opt_val, "item") and getattr(opt_val, "ndim", 0) > 0:
                opt_val = opt_val.item()
            else:
                opt_val = float(opt_val)

            self.opt_params_dict = {
                col: float(val) for col, val in zip(input_cols, opt_params)
            }

            # Update Optimization KPI Cards
            self._on_opt_goal_change()
            self.kpi_opt["val_var"].set(f"{opt_val:.6g}")
            self.kpi_opt["sub_var"].set(f"Target: {output_col}")

            converged = True
            if hasattr(result, "last_opt_result") and result.last_opt_result is not None:
                opt_res = result.last_opt_result
                converged = bool(opt_res.success)

            # Populate Structured Tables (Tab 1)
            for item in self.opt_params_tree.get_children():
                self.opt_params_tree.delete(item)
            for col, val in zip(input_cols, opt_params):
                self.opt_params_tree.insert(
                    "",
                    tk.END,
                    values=(
                        col,
                        f"{val:.6f}",
                        bounds_display.get(col, "Unconstrained"),
                        self._get_col_range_str(col),
                    ),
                )

            for item in self.constraint_eval_tree.get_children():
                self.constraint_eval_tree.delete(item)

            n_violated = 0
            constraint_report_lines = []
            if self.linear_constraints:
                for i, c in enumerate(self.linear_constraints, 1):
                    lhs_val = sum(c["coeffs"].get(col, 0.0) * val for col, val in zip(input_cols, opt_params))
                    op = c["operator"]
                    b = c["bound"]
                    tol = 1e-4
                    if op == "<=":
                        satisfied = lhs_val <= b + tol
                    elif op == ">=":
                        satisfied = lhs_val >= b - tol
                    elif op == "==":
                        satisfied = abs(lhs_val - b) <= tol
                    else:
                        satisfied = True

                    if not satisfied:
                        n_violated += 1
                    status_str = "Satisfied" if satisfied else "VIOLATED"
                    tag = "satisfied" if satisfied else "violated"
                    self.constraint_eval_tree.insert(
                        "",
                        tk.END,
                        values=(i, c["expression_str"], f"{lhs_val:.6f}", status_str),
                        tags=(tag,),
                    )
                    constraint_report_lines.append(
                        f"  [{i}] {c['expression_str']}\n"
                        f"      Evaluated LHS = {lhs_val:.6f} [{status_str}]\n"
                    )

            if converged and n_violated == 0:
                self.kpi_status["val_var"].set("Converged")
                self.kpi_status["sub_var"].set(
                    f"{len(self.linear_constraints)} constraint(s) satisfied"
                    if self.linear_constraints
                    else f"{goal}d successfully"
                )
                self.kpi_status["accent"].config(bg=PALETTE["success"])
            else:
                self.kpi_status["val_var"].set("Check Status")
                self.kpi_status["sub_var"].set(
                    f"{n_violated} constraint violation(s)" if n_violated else "Optimizer warning"
                )
                self.kpi_status["accent"].config(bg=PALETTE["warning"])

            # Build Optimization Report Section & refresh Full Report (Tab 2)
            opt_lines = ["=== RSM Optimization Results ===\n\n"]
            opt_lines.append(f"Optimization Goal: {goal} '{output_col}'\n")
            if hasattr(result, "last_opt_result") and result.last_opt_result is not None:
                opt_res = result.last_opt_result
                if opt_res.success:
                    opt_lines.append("Optimizer Status: Converged successfully\n\n")
                else:
                    opt_lines.append(f"Optimizer Status: Warning - {opt_res.message}\n\n")

            opt_lines.append("Optimized Input Parameters:\n")
            for col, val in zip(input_cols, opt_params):
                opt_lines.append(f"  - {col}: {val:.6f}\n")

            extremum_lbl = "Maximum" if is_maximize else "Minimum"
            opt_lines.append(
                f"\nOptimized ({extremum_lbl}) Output Value [{output_col}]: {opt_val:.6f}\n"
            )

            if constraint_report_lines:
                opt_lines.append("\nLinear Constraint Verification:\n")
                opt_lines.extend(constraint_report_lines)

            self.last_opt_report_text = "".join(opt_lines)
            self._render_full_report()

            short_lbl = "Max" if is_maximize else "Min"
            self.status_var.set(
                f"Optimization complete (no refit) — {result.method} ({short_lbl} {output_col} = {opt_val:.6g})."
            )

        except Exception as e:
            self.status_var.set("Optimization failed — check error dialog.")
            messagebox.showerror(
                "Error", f"An error occurred during RSM optimization:\n{e!s}"
            )

    # =========================================================================
    # Plot Configuration Window & Smart Defaults
    # =========================================================================

    def _get_col_plot_defaults(self, col):
        """
        Return smart defaults (min_str, max_str, fixed_str, pq_values_str) for a column
        based on dataset statistics and the latest optimized solution.
        """
        min_v, max_v = -1.0, 1.0
        mean_v = 0.0
        if self.df is not None and col in self.df.columns:
            series = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if not series.empty:
                min_v = float(series.min())
                max_v = float(series.max())
                mean_v = float(series.mean())
                if np.isclose(min_v, max_v):
                    min_v -= 1.0
                    max_v += 1.0

        opt_v = self.opt_params_dict.get(col, mean_v)
        q25 = min_v + 0.25 * (max_v - min_v)
        q50 = min_v + 0.50 * (max_v - min_v)
        q75 = min_v + 0.75 * (max_v - min_v)
        pq_str = f"{q25:.4g}, {q50:.4g}, {q75:.4g}"
        return f"{min_v:.4g}", f"{max_v:.4g}", f"{opt_v:.6g}", pq_str

    def open_plot_config(self):
        if not self.result or not self.current_input_cols:
            return

        if self.plot_config_win is not None and self.plot_config_win.winfo_exists():
            self.plot_config_win.destroy()

        config_win = tk.Toplevel(self)
        self.plot_config_win = config_win
        config_win.title("Configure Multi-Dimensional Contour Plot")
        config_win.geometry("780x720")
        config_win.minsize(680, 600)
        config_win.configure(bg=PALETTE["bg_main"])

        notebook = ttk.Notebook(config_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))

        # ---------------------------------------------------------------------
        # TAB 1: Roles
        # ---------------------------------------------------------------------
        roles_frame = ttk.Frame(notebook, style="Card.TFrame", padding="14")
        notebook.add(roles_frame, text="  1. Parameter Roles & Ranges  ")

        roles_top = ttk.Frame(roles_frame, style="Card.TFrame")
        roles_top.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            roles_top,
            text="Assign each input variable to a plot axis, subplot grid (P/Q), or fixed slice value:",
            style="CardBold.TLabel",
        ).pack(side=tk.LEFT)

        roles_actions = ttk.Frame(roles_frame, style="Card.TFrame")
        roles_actions.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(
            roles_actions,
            text="Reset X/Y Ranges to Data [Min, Max]",
            style="Small.TButton",
            command=self._reset_plot_axes_to_data,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            roles_actions,
            text="Set Fixed Values to Optimal Solution",
            style="Small.TButton",
            command=self._set_plot_fixed_to_optimal,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            roles_actions,
            text="Set Fixed Values to Data Mean",
            style="Small.TButton",
            command=self._set_plot_fixed_to_mean,
        ).pack(side=tk.LEFT)

        # Scrollable Roles List
        roles_canvas_wrap = ttk.Frame(roles_frame, style="Card.TFrame")
        roles_canvas_wrap.pack(fill=tk.BOTH, expand=True)

        roles_canvas = tk.Canvas(
            roles_canvas_wrap,
            bg=PALETTE["bg_card"],
            bd=0,
            highlightthickness=0,
        )
        roles_scroll = ttk.Scrollbar(
            roles_canvas_wrap, orient=tk.VERTICAL, command=roles_canvas.yview
        )
        roles_list_frame = ttk.Frame(roles_canvas, style="Card.TFrame")
        roles_list_frame.bind(
            "<Configure>",
            lambda e: roles_canvas.configure(scrollregion=roles_canvas.bbox("all")),
        )
        roles_win_id = roles_canvas.create_window(
            (0, 0), window=roles_list_frame, anchor="nw"
        )
        roles_canvas.bind(
            "<Configure>",
            lambda e: roles_canvas.itemconfigure(roles_win_id, width=e.width),
        )
        roles_canvas.configure(yscrollcommand=roles_scroll.set)
        roles_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        roles_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.plot_param_configs = {}
        roles = ["X-Axis", "Y-Axis", "Row-Axis (P)", "Column-Axis (Q)", "Fixed"]

        for idx, col in enumerate(self.current_input_cols):
            row_frame = ttk.Frame(roles_list_frame, style="Card.TFrame")
            row_frame.pack(fill=tk.X, pady=5)

            ttk.Label(row_frame, text=col, width=16, style="CardBold.TLabel").pack(
                side=tk.LEFT
            )

            role_var = tk.StringVar()
            role_combo = ttk.Combobox(
                row_frame,
                textvariable=role_var,
                values=roles,
                state="readonly",
                width=15,
            )
            role_combo.pack(side=tk.LEFT, padx=6)

            input_frame = ttk.Frame(row_frame, style="Card.TFrame")
            input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

            self.plot_param_configs[col] = {
                "role_var": role_var,
                "input_frame": input_frame,
                "vars": {},
            }

            def on_role_change(event, c=col):
                self._update_plot_role_inputs(c)

            role_combo.bind("<<ComboboxSelected>>", on_role_change)

            if idx == 0:
                role_combo.set("X-Axis")
            elif idx == 1:
                role_combo.set("Y-Axis")
            else:
                role_combo.set("Fixed")

            self._update_plot_role_inputs(col)

        # ---------------------------------------------------------------------
        # TAB 2: Labels
        # ---------------------------------------------------------------------
        labels_frame = ttk.Frame(notebook, style="Card.TFrame", padding="14")
        notebook.add(labels_frame, text="  2. Titles & Axis Labels  ")

        def add_label_field(parent, text, default_val):
            frame = ttk.Frame(parent, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=6)
            ttk.Label(frame, text=text, width=36, style="Card.TLabel").pack(side=tk.LEFT)
            var = tk.StringVar(value=default_val)
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            return var

        out_col_name = self.output_combo.get() or "Response"
        self.plot_title_var = add_label_field(
            labels_frame, "Plot Title:", f"RSM Contour Plot — {out_col_name}"
        )
        self.x_label_var = add_label_field(
            labels_frame, "X-Axis Label (Leave empty for column name):", ""
        )
        self.y_label_var = add_label_field(
            labels_frame, "Y-Axis Label (Leave empty for column name):", ""
        )
        self.colorbar_label_var = add_label_field(
            labels_frame, "Colorbar Label:", out_col_name
        )
        self.p_label_prefix_var = add_label_field(
            labels_frame, "Row-Axis (P) Label Prefix:", ""
        )
        self.p_label_suffix_var = add_label_field(
            labels_frame, "Row-Axis (P) Label Suffix:", ""
        )
        self.q_label_prefix_var = add_label_field(
            labels_frame, "Column-Axis (Q) Label Prefix:", ""
        )
        self.q_label_suffix_var = add_label_field(
            labels_frame, "Column-Axis (Q) Label Suffix:", ""
        )

        # ---------------------------------------------------------------------
        # TAB 3: Advanced Settings (Grouped Two-Column Layout)
        # ---------------------------------------------------------------------
        adv_frame = ttk.Frame(notebook, style="Card.TFrame", padding="12")
        notebook.add(adv_frame, text="  3. Styling, Scatter & Uncertainty  ")
        adv_frame.columnconfigure(0, weight=1)
        adv_frame.columnconfigure(1, weight=1)

        self.adv_settings_vars = {}
        self.adv_settings_widgets = {}

        def add_adv_field(
            parent,
            key,
            text,
            default_val,
            var_type=tk.StringVar,
            options=None,
            readonly_options=True,
        ):
            frame = ttk.Frame(parent, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=3)
            ttk.Label(frame, text=text, width=24, style="Card.TLabel").pack(side=tk.LEFT)
            var = var_type(value=default_val)

            if var_type == tk.BooleanVar:
                widget = ttk.Checkbutton(frame, variable=var)
                if text.startswith("Plot Uncertainty") and not getattr(
                    self.result, "supports_uncertainty", False
                ):
                    widget.config(state="disabled")
                widget.pack(side=tk.LEFT)
            elif options is not None:
                state = "readonly" if readonly_options else "normal"
                widget = ttk.Combobox(
                    frame, textvariable=var, values=options, state=state, width=16
                )
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=16)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.adv_settings_vars[key] = var
            self.adv_settings_widgets[key] = widget
            return var

        # Group 1 (Left): Contour & Surface Styling
        contour_group = ttk.LabelFrame(
            adv_frame, text="Contour & Surface Styling", padding="10"
        )
        contour_group.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 6), pady=(0, 8))

        add_adv_field(
            contour_group,
            "cmap",
            "Colormap (cmap):",
            "plasma",
            options=COMMON_CMAPS,
            readonly_options=False,
        )
        add_adv_field(contour_group, "alpha", "Alpha (transparency):", 0.85, tk.DoubleVar)
        add_adv_field(contour_group, "fill_levels", "Fill Levels:", 100, tk.IntVar)
        add_adv_field(contour_group, "line_levels", "Line Levels:", 10, tk.IntVar)
        add_adv_field(contour_group, "line_color", "Line Color:", "white")
        add_adv_field(contour_group, "inline_color", "Inline Color:", "white")
        add_adv_field(contour_group, "inline_fontsize", "Inline Fontsize:", 9, tk.IntVar)
        add_adv_field(contour_group, "inline_format", "Inline Format:", "%1.1f")

        # Group 2 (Left Bottom): Grid, Colorbar & Uncertainty
        scale_group = ttk.LabelFrame(
            adv_frame, text="Colorbar, Grid & Uncertainty", padding="10"
        )
        scale_group.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 6), pady=(0, 4))

        add_adv_field(scale_group, "uniform_cmap", "Uniform Colormap:", True, tk.BooleanVar)
        add_adv_field(scale_group, "show_colorbar", "Show Colorbar:", False, tk.BooleanVar)

        cbar_lbl_frame = ttk.Frame(scale_group, style="Card.TFrame")
        cbar_lbl_frame.pack(fill=tk.X, pady=3)
        ttk.Label(cbar_lbl_frame, text="Colorbar Label:", width=24, style="Card.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Entry(cbar_lbl_frame, textvariable=self.colorbar_label_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        self.adv_settings_vars["colorbar_label"] = self.colorbar_label_var

        add_adv_field(scale_group, "grid_color", "Grid Color:", "gray")
        add_adv_field(
            scale_group,
            "grid_linestyle",
            "Grid Linestyle:",
            "--",
            options=COMMON_LINESTYLES,
            readonly_options=False,
        )
        add_adv_field(
            scale_group,
            "plot_uncertainty",
            "Plot Uncertainty:",
            False,
            tk.BooleanVar,
        )

        # Group 3 (Right): Measurement Data Scatter Overlay
        scatter_group = ttk.LabelFrame(
            adv_frame, text="Measurement Data Scatter Overlay", padding="10"
        )
        scatter_group.grid(row=0, column=1, rowspan=2, sticky=tk.NSEW, padx=(6, 0), pady=(0, 4))

        add_adv_field(
            scatter_group, "scatter_data", "Scatter-Plot Data:", False, tk.BooleanVar
        )
        add_adv_field(
            scatter_group, "scatter_size", "Scatter Marker Size:", 30.0, tk.DoubleVar
        )
        add_adv_field(
            scatter_group,
            "scatter_color_mode",
            "Scatter Color Mode:",
            "Fixed Color",
            options=["Fixed Color", "Output Value (Colormap)"],
            readonly_options=True,
        )
        add_adv_field(scatter_group, "scatter_color", "Scatter Marker Color:", "white")
        add_adv_field(
            scatter_group,
            "scatter_cmap",
            "Scatter Colormap:",
            "plasma",
            options=COMMON_CMAPS,
            readonly_options=False,
        )
        add_adv_field(
            scatter_group, "scatter_edgecolor", "Scatter Edge Color:", "black"
        )
        add_adv_field(
            scatter_group,
            "scatter_marker",
            "Scatter Marker Style:",
            "o",
            options=COMMON_MARKERS,
            readonly_options=False,
        )

        self.adv_settings_widgets["scatter_color_mode"].bind(
            "<<ComboboxSelected>>", lambda e: self._update_scatter_color_state()
        )
        self._update_scatter_color_state()

        # ---------------------------------------------------------------------
        # Footer Action Bar
        # ---------------------------------------------------------------------
        btn_frame = ttk.Frame(config_win, padding=(12, 6, 12, 12))
        btn_frame.pack(fill=tk.X)
        ttk.Button(
            btn_frame, text="Load Settings...", command=self.load_plot_settings
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            btn_frame, text="Save Settings...", command=self.save_plot_settings
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_frame,
            text="▶  Generate Plot",
            style="Primary.TButton",
            command=self.generate_plot,
        ).pack(side=tk.RIGHT)

    def _reset_plot_axes_to_data(self):
        for col, param_data in self.plot_param_configs.items():
            role = param_data["role_var"].get()
            if role in ("X-Axis", "Y-Axis"):
                min_s, max_s, _, _ = self._get_col_plot_defaults(col)
                if "min" in param_data["vars"]:
                    param_data["vars"]["min"].set(min_s)
                if "max" in param_data["vars"]:
                    param_data["vars"]["max"].set(max_s)

    def _set_plot_fixed_to_optimal(self):
        for col, param_data in self.plot_param_configs.items():
            if param_data["role_var"].get() == "Fixed" and "value" in param_data["vars"]:
                _, _, opt_s, _ = self._get_col_plot_defaults(col)
                param_data["vars"]["value"].set(opt_s)

    def _set_plot_fixed_to_mean(self):
        for col, param_data in self.plot_param_configs.items():
            if param_data["role_var"].get() == "Fixed" and "value" in param_data["vars"]:
                mean_v = 0.0
                if self.df is not None and col in self.df.columns:
                    s = pd.to_numeric(self.df[col], errors="coerce").dropna()
                    if not s.empty:
                        mean_v = float(s.mean())
                param_data["vars"]["value"].set(f"{mean_v:.6g}")

    def _update_scatter_color_state(self):
        if not hasattr(self, "adv_settings_vars") or not hasattr(self, "adv_settings_widgets"):
            return
        mode_var = self.adv_settings_vars.get("scatter_color_mode")
        color_entry = self.adv_settings_widgets.get("scatter_color")
        cmap_entry = self.adv_settings_widgets.get("scatter_cmap")
        if mode_var is None or color_entry is None or cmap_entry is None:
            return
        if mode_var.get() == "Output Value (Colormap)":
            color_entry.config(state="disabled")
            cmap_entry.config(state="normal")
        else:
            color_entry.config(state="normal")
            cmap_entry.config(state="disabled")

    def _update_plot_role_inputs(self, col):
        param_data = self.plot_param_configs[col]
        role = param_data["role_var"].get()
        input_frame = param_data["input_frame"]

        for widget in input_frame.winfo_children():
            widget.destroy()

        param_data["vars"] = {}
        min_def, max_def, fixed_def, pq_def = self._get_col_plot_defaults(col)

        if role in ["X-Axis", "Y-Axis"]:
            min_var = tk.StringVar(value=min_def)
            max_var = tk.StringVar(value=max_def)
            steps_var = tk.StringVar(value="50")

            ttk.Label(input_frame, text="Min:", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=min_var, width=9).pack(
                side=tk.LEFT, padx=(3, 8)
            )

            ttk.Label(input_frame, text="Max:", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=max_var, width=9).pack(
                side=tk.LEFT, padx=(3, 8)
            )

            ttk.Label(input_frame, text="Steps:", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(input_frame, textvariable=steps_var, width=6).pack(
                side=tk.LEFT, padx=(3, 0)
            )

            param_data["vars"]["min"] = min_var
            param_data["vars"]["max"] = max_var
            param_data["vars"]["steps"] = steps_var

        elif role in ["Row-Axis (P)", "Column-Axis (Q)"]:
            val_var = tk.StringVar(value=pq_def)
            ttk.Label(
                input_frame, text="Values (comma-separated):", style="Card.TLabel"
            ).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Entry(input_frame, textvariable=val_var).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )
            param_data["vars"]["values"] = val_var

        elif role == "Fixed":
            val_var = tk.StringVar(value=fixed_def)
            ttk.Label(input_frame, text="Hold Value:", style="Card.TLabel").pack(
                side=tk.LEFT, padx=(0, 4)
            )
            ttk.Entry(input_frame, textvariable=val_var, width=12).pack(side=tk.LEFT)
            ttk.Label(
                input_frame,
                text=f"  (Data: {self._get_col_range_str(col)})",
                style="CardMuted.TLabel",
            ).pack(side=tk.LEFT, padx=(6, 0))
            param_data["vars"]["value"] = val_var

    def generate_plot(self):
        config = {'fixed': []}
        x_count = y_count = p_count = q_count = 0

        label_arrays_p = None
        label_arrays_q = None

        x_col = None
        y_col = None

        try:
            for idx, col in enumerate(self.current_input_cols):
                param_data = self.plot_param_configs[col]
                role = param_data["role_var"].get()
                vars_dict = param_data["vars"]

                if role == "X-Axis":
                    x_count += 1
                    min_v = float(vars_dict["min"].get())
                    max_v = float(vars_dict["max"].get())
                    steps_v = int(vars_dict["steps"].get())
                    config['x'] = (idx, np.linspace(min_v, max_v, steps_v))
                    x_col = col
                elif role == "Y-Axis":
                    y_count += 1
                    min_v = float(vars_dict["min"].get())
                    max_v = float(vars_dict["max"].get())
                    steps_v = int(vars_dict["steps"].get())
                    config['y'] = (idx, np.linspace(min_v, max_v, steps_v))
                    y_col = col
                elif role == "Row-Axis (P)":
                    p_count += 1
                    val_strs = vars_dict["values"].get().split(",")
                    vals = [float(v.strip()) for v in val_strs if v.strip()]
                    config['p'] = (idx, vals)

                    p_prefix = self.p_label_prefix_var.get().strip()
                    p_suffix = self.p_label_suffix_var.get().strip()
                    if not p_prefix:
                        p_prefix = f"{col}="
                    label_arrays_p = [f"{p_prefix}{v}{p_suffix}" for v in vals]

                elif role == "Column-Axis (Q)":
                    q_count += 1
                    val_strs = vars_dict["values"].get().split(",")
                    vals = [float(v.strip()) for v in val_strs if v.strip()]
                    config['q'] = (idx, vals)

                    q_prefix = self.q_label_prefix_var.get().strip()
                    q_suffix = self.q_label_suffix_var.get().strip()
                    if not q_prefix:
                        q_prefix = f"{col}="
                    label_arrays_q = [f"{q_prefix}{v}{q_suffix}" for v in vals]

                elif role == "Fixed":
                    val = float(vars_dict["value"].get())
                    config['fixed'].append((idx, val))

            if x_count != 1 or y_count != 1:
                messagebox.showerror("Error", "You must assign exactly one X-Axis and one Y-Axis.")
                return
            if p_count > 1 or q_count > 1:
                messagebox.showerror("Error", "You can assign at most one Row-Axis (P) and one Column-Axis (Q).")
                return

            x_label = self.x_label_var.get().strip()
            if not x_label:
                x_label = x_col

            y_label = self.y_label_var.get().strip()
            if not y_label:
                y_label = y_col

            title = self.plot_title_var.get().strip()
            if not title:
                title = "RSM Contour Plot"

            label_array = None
            if p_count > 0 or q_count > 0:
                p_labels = label_arrays_p if label_arrays_p else [""]
                q_labels = label_arrays_q if label_arrays_q else [""]
                label_array = []
                for p_lbl in p_labels:
                    row_labels = []
                    for q_lbl in q_labels:
                        if p_lbl and q_lbl:
                            row_labels.append(f"{p_lbl}, {q_lbl}")
                        else:
                            row_labels.append(p_lbl or q_lbl)
                    label_array.append(row_labels)

            # Gather advanced plot settings
            plot_settings = {}
            for k, var in self.adv_settings_vars.items():
                plot_settings[k] = var.get()

            if plot_settings.get('plot_uncertainty', False) and not getattr(self.result, 'supports_uncertainty', False):
                messagebox.showerror("Error", f"Uncertainty plotting is not supported for {getattr(self.result, 'method', 'this model')}.")
                return

            self.status_var.set("Generating contour visualization...")
            self.update_idletasks()
            self.result.visualize_rsm(config, title=title, xlabel=x_label, ylabel=y_label, label_array=label_array, plot_settings=plot_settings)
            self.status_var.set("Contour plot displayed.")

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def save_plot_settings(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Plot Settings"
        )
        if not filepath:
            return

        settings = {
            "roles": {},
            "labels": {
                "plot_title": self.plot_title_var.get(),
                "x_label": self.x_label_var.get(),
                "y_label": self.y_label_var.get(),
                "colorbar_label": self.colorbar_label_var.get(),
                "p_label_prefix": self.p_label_prefix_var.get(),
                "p_label_suffix": self.p_label_suffix_var.get(),
                "q_label_prefix": self.q_label_prefix_var.get(),
                "q_label_suffix": self.q_label_suffix_var.get(),
            },
            "advanced": {}
        }

        for col, config in self.plot_param_configs.items():
            role = config["role_var"].get()
            role_data = {"role": role, "vars": {}}
            for var_name, var_obj in config["vars"].items():
                role_data["vars"][var_name] = var_obj.get()
            settings["roles"][col] = role_data

        for key, var in self.adv_settings_vars.items():
            if key == "colorbar_label":
                continue
            settings["advanced"][key] = var.get()

        try:
            with open(filepath, "w") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", f"Plot settings saved successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def load_plot_settings(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Plot Settings"
        )
        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                settings = json.load(f)

            if "labels" in settings:
                labels = settings["labels"]
                if "plot_title" in labels:
                    self.plot_title_var.set(labels["plot_title"])
                if "x_label" in labels:
                    self.x_label_var.set(labels["x_label"])
                if "y_label" in labels:
                    self.y_label_var.set(labels["y_label"])
                if "colorbar_label" in labels:
                    self.colorbar_label_var.set(labels["colorbar_label"])
                if "p_label_prefix" in labels:
                    self.p_label_prefix_var.set(labels["p_label_prefix"])
                if "p_label_suffix" in labels:
                    self.p_label_suffix_var.set(labels["p_label_suffix"])
                if "q_label_prefix" in labels:
                    self.q_label_prefix_var.set(labels["q_label_prefix"])
                if "q_label_suffix" in labels:
                    self.q_label_suffix_var.set(labels["q_label_suffix"])

            if "advanced" in settings:
                for key, val in settings["advanced"].items():
                    if key in self.adv_settings_vars:
                        if key == "plot_uncertainty" and val:
                            if not getattr(self.result, "supports_uncertainty", False):
                                self.adv_settings_vars[key].set(False)
                                method_name = getattr(self.result, "method", "this model")
                                messagebox.showinfo(
                                    "Setting Overridden",
                                    f"Uncertainty plotting was enabled in the loaded configuration, "
                                    f"but the current model ({method_name}) does not support uncertainty prediction. "
                                    f"The setting has been overridden to False."
                                )
                                continue
                        self.adv_settings_vars[key].set(val)
                self._update_scatter_color_state()

            if "roles" in settings:
                for col, role_data in settings["roles"].items():
                    if col in self.plot_param_configs:
                        config = self.plot_param_configs[col]
                        config["role_var"].set(role_data.get("role", "Fixed"))
                        self._update_plot_role_inputs(col)
                        if "vars" in role_data:
                            for var_name, var_val in role_data["vars"].items():
                                if var_name in config["vars"]:
                                    config["vars"][var_name].set(var_val)

            messagebox.showinfo("Success", f"Plot settings loaded successfully from:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")


if __name__ == "__main__":
    app = RSMGui()
    app.mainloop()
