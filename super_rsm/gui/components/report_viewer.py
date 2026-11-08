"""
super_rsm/gui/components/report_viewer.py

Rich Markdown-to-HTML Report Viewer widget with inline diagnostic graphs and image export.
Uses `markdown` + `tkinterweb.HtmlFrame` when available for CSS-styled HTML tables and
inline base64 plots, with an automatic rich `tk.Text` + `tk.PhotoImage` fallback.
"""

import html
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from super_rsm.gui.styles.palette import PALETTE
from super_rsm.gui.styles.theme import get_ui_fonts
from super_rsm.visualization.diagnostic_plots import (
    figure_to_base64_png,
    figure_to_png_bytes,
    save_figure,
)

try:
    import markdown as _md_pkg
except ImportError:
    _md_pkg = None

try:
    from tkinterweb import HtmlFrame as _HtmlFrame
except ImportError:
    _HtmlFrame = None

PLOT_CAPTIONS: Dict[str, str] = {
    "parity": "Diagnostic Plot 1: Actual vs. Predicted Parity",
    "t_value": "Diagnostic Plot 2: Parameter Effect Magnitude (|t-Value|)",
    "p_value": "Diagnostic Plot 3: Statistical Significance (p-Values)",
    "importance": "Diagnostic Plot 4: Relative Parameter / Factor Importance",
    "significance": "Diagnostic Plot: Parameter Significance & p-Values",
}

REPORT_CSS = f"""
body {{ font-family: "Segoe UI", sans-serif; font-size: 13px; color: {PALETTE['text_main']}; background-color: {PALETTE['bg_subtle']}; margin: 12px 16px; line-height: 1.5; }}
h1 {{ font-size: 17px; color: {PALETTE['accent']}; border-bottom: 2px solid {PALETTE['border']}; padding-bottom: 5px; margin: 4px 0 10px 0; }}
h2 {{ font-size: 14px; color: {PALETTE['text_main']}; background-color: #E2E8F0; padding: 5px 10px; border-left: 4px solid {PALETTE['accent']}; margin: 16px 0 8px 0; }}
h3 {{ font-size: 13px; color: {PALETTE['text_secondary']}; margin: 12px 0 6px 0; }}
ul {{ margin: 4px 0 10px 0; padding-left: 22px; }}
li {{ margin-bottom: 3px; }}
code {{ font-family: Consolas, Menlo, monospace; background-color: #E2E8F0; padding: 1px 5px; font-size: 12px; }}
pre {{ font-family: Consolas, Menlo, monospace; background-color: #FFFFFF; border: 1px solid {PALETTE['border']}; padding: 10px 12px; font-size: 12px; margin: 8px 0; }}
pre code {{ background-color: transparent; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0 12px 0; background-color: #FFFFFF; border: 1px solid {PALETTE['border']}; font-size: 12px; }}
th {{ background-color: #EFF6FF; color: {PALETTE['text_main']}; font-weight: bold; border: 1px solid {PALETTE['border']}; padding: 6px 8px; text-align: left; }}
td {{ border: 1px solid {PALETTE['border_light']}; padding: 5px 8px; }}
tr:nth-child(even) td {{ background-color: {PALETTE['bg_subtle']}; }}
.plot-card {{ background-color: #FFFFFF; border: 1px solid {PALETTE['border']}; padding: 10px; margin: 12px 0; text-align: center; }}
.plot-toolbar {{ margin-top: 6px; padding-top: 6px; border-top: 1px solid {PALETTE['border_light']}; font-size: 12px; color: {PALETTE['text_secondary']}; }}
.edit-btn {{ display: inline-block; background-color: #475569; color: #FFFFFF; text-decoration: none; font-weight: bold; padding: 4px 10px; margin-left: 12px; }}
.save-btn {{ display: inline-block; background-color: {PALETTE['accent']}; color: #FFFFFF; text-decoration: none; font-weight: bold; padding: 4px 10px; margin-left: 6px; }}
"""


def compile_markdown_to_html(markdown_text: str, figures: Optional[Dict[str, Any]] = None) -> str:
    """Compile Markdown report text and diagnostic figures into a styled HTML document."""
    if not markdown_text:
        return f"<html><head><style>{REPORT_CSS}</style></head><body></body></html>"

    body_html = (
        _md_pkg.markdown(markdown_text, extensions=["tables", "fenced_code"])
        if _md_pkg is not None
        else _fallback_markdown_to_html(markdown_text)
    )

    if figures:
        for key, fig in figures.items():
            if fig is None:
                continue
            b64_str = figure_to_base64_png(fig, dpi=105)
            caption = html.escape(PLOT_CAPTIONS.get(key, f"Diagnostic Plot ({key})"))
            card_html = (
                f'<div class="plot-card"><div><img src="data:image/png;base64,{b64_str}" alt="{caption}" /></div>'
                f'<div class="plot-toolbar"><strong>{caption}</strong> '
                f'<a href="edit_plot:{key}" class="edit-btn">Edit Plot...</a>'
                f'<a href="save_plot:{key}" class="save-btn">Save Image...</a></div></div>'
            )
            body_html = body_html.replace(f"<!-- PLOT:{key} -->", card_html)

    body_html = re.sub(r"<!--\s*PLOT:\w+\s*-->", "", body_html)
    return f"<html><head><meta charset='utf-8'><style>{REPORT_CSS}</style></head><body>{body_html}</body></html>"


def _fallback_markdown_to_html(md_text: str) -> str:
    """Lightweight Markdown-to-HTML converter when `markdown` package is absent."""
    out: List[str] = []
    in_ul = in_code = in_table = False

    def _inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<!-- PLOT:"):
            if in_ul: out.append("</ul>"); in_ul = False
            if in_table: out.append("</tbody></table>"); in_table = False
            out.append(stripped); continue
        if stripped.startswith("```"):
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code; continue
        if in_code:
            out.append(html.escape(line)); continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells): continue
            if not in_table:
                if in_ul: out.append("</ul>"); in_ul = False
                out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells) + "</tr></thead><tbody>")
                in_table = True
            else:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            out.append("</tbody></table>"); in_table = False

        if stripped.startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline(stripped[2:])}</li>"); continue
        elif in_ul:
            out.append("</ul>"); in_ul = False

        if stripped.startswith("# "): out.append(f"<h1>{_inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "): out.append(f"<h2>{_inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "): out.append(f"<h3>{_inline(stripped[4:])}</h3>")
        elif stripped: out.append(f"<p>{_inline(stripped)}</p>")

    if in_ul: out.append("</ul>")
    if in_table: out.append("</tbody></table>")
    if in_code: out.append("</code></pre>")
    return "\n".join(out)


class ReportViewer(tk.Frame):
    """Rich report display widget supporting HTML rendering and styled tk.Text + PhotoImage fallback."""

    def __init__(
        self,
        parent: tk.Misc,
        fonts: Optional[Dict[str, tuple]] = None,
        on_edit_plot: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent, bg=PALETTE["border"], bd=1, relief=tk.FLAT)
        self.fonts = fonts or get_ui_fonts()
        self.on_edit_plot = on_edit_plot
        self._markdown_source: str = ""
        self._html_source: str = ""
        self._figures: Dict[str, Any] = {}
        self._photo_refs: List[tk.PhotoImage] = []
        self._embedded_frames: List[tk.Widget] = []

        text_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.text_widget = tk.Text(
            self, height=12, state="disabled", bg=PALETTE["bg_subtle"], fg=PALETTE["text_main"],
            font=self.fonts["body"], bd=0, padx=12, pady=10, wrap=tk.WORD, yscrollcommand=text_scroll.set,
        )
        text_scroll.config(command=self.text_widget.yview)
        self._configure_text_tags()

        self.html_frame: Optional[Any] = None
        if _HtmlFrame is not None:
            try:
                self.html_frame = _HtmlFrame(self, messages_enabled=False)
                if hasattr(self.html_frame, "on_link_click"):
                    self.html_frame.on_link_click(self._on_html_link_click)
                self.html_frame.pack(fill=tk.BOTH, expand=True)
            except Exception:
                self.html_frame = None

        if self.html_frame is None:
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _configure_text_tags(self) -> None:
        base_fam, mono_fam = self.fonts["body"][0], self.fonts["mono"][0]
        self.text_widget.tag_configure("h1", font=(base_fam, 13, "bold"), foreground=PALETTE["accent"], spacing1=4, spacing3=6)
        self.text_widget.tag_configure("h2", font=(base_fam, 10, "bold"), foreground=PALETTE["text_main"], background="#E2E8F0", spacing1=10, spacing3=4)
        self.text_widget.tag_configure("h3", font=(base_fam, 9, "bold"), foreground=PALETTE["text_secondary"], spacing1=6, spacing3=2)
        self.text_widget.tag_configure("bold", font=self.fonts["body_bold"])
        self.text_widget.tag_configure("italic", font=(base_fam, 9, "italic"), foreground=PALETTE["text_secondary"])
        self.text_widget.tag_configure("code", font=self.fonts["mono"], background="#E2E8F0")
        self.text_widget.tag_configure("code_block", font=(mono_fam, 9), background="#FFFFFF", lmargin1=12, lmargin2=12, spacing1=4, spacing3=4)
        self.text_widget.tag_configure("bullet", lmargin1=14, lmargin2=26, spacing1=1, spacing3=1)
        self.text_widget.tag_configure("table_hdr", font=(mono_fam, 9, "bold"), background="#DBEAFE", foreground=PALETTE["text_main"])
        self.text_widget.tag_configure("table_even", font=(mono_fam, 9), background="#FFFFFF")
        self.text_widget.tag_configure("table_odd", font=(mono_fam, 9), background=PALETTE["bg_subtle"])

    def _on_html_link_click(self, url: str) -> None:
        if url.startswith("save_plot:"):
            self.prompt_save_figure(url.split(":", 1)[1])
        elif url.startswith("edit_plot:"):
            self.prompt_edit_figure(url.split(":", 1)[1])

    def prompt_edit_figure(self, plot_key: str) -> None:
        """Invoke inline plot editor callback for the selected diagnostic plot."""
        if self.on_edit_plot is not None:
            self.on_edit_plot(plot_key)

    def prompt_save_figure(self, plot_key: str) -> Optional[str]:
        """Open file save dialog to export an inline diagnostic plot."""
        fig = self._figures.get(plot_key)
        if fig is None:
            return None
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"rsm_{plot_key}_plot.png",
            filetypes=[("PNG Image (300 DPI)", "*.png"), ("SVG Vector Image", "*.svg"), ("PDF Document", "*.pdf"), ("All Files", "*.*")],
            title=f"Save {PLOT_CAPTIONS.get(plot_key, 'Diagnostic Plot')}",
            parent=self.winfo_toplevel(),
        )
        if not filepath:
            return None
        try:
            save_figure(fig, filepath, dpi=300)
            messagebox.showinfo("Image Saved", f"Diagnostic plot saved successfully to:\n{filepath}", parent=self.winfo_toplevel())
            return filepath
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save image:\n{exc!s}", parent=self.winfo_toplevel())
            return None

    def set_report(self, markdown_text: str, figures: Optional[Dict[str, Any]] = None) -> None:
        """Render Markdown report and inline diagnostic figures."""
        self._markdown_source = markdown_text or ""
        self._figures = dict(figures) if figures else {}
        self._html_source = compile_markdown_to_html(self._markdown_source, self._figures)
        if self.html_frame is not None:
            try:
                self.html_frame.load_html(self._html_source)
            except Exception:
                pass
        self._render_into_text_widget(self._markdown_source, self._figures)

    def _render_into_text_widget(self, md_text: str, figures: Dict[str, Any]) -> None:
        for w in self._embedded_frames:
            try: w.destroy()
            except tk.TclError: pass
        self._embedded_frames.clear()
        self._photo_refs.clear()

        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        if not md_text:
            self.text_widget.config(state="disabled")
            return

        in_code = False
        table_buffer: List[List[str]] = []

        def _flush_table() -> None:
            if not table_buffer: return
            n_cols = max(len(r) for r in table_buffer)
            widths = [max(len(r[c].replace("**", "").replace("*", "")) if c < len(r) else 0 for r in table_buffer) for c in range(n_cols)]
            for r_idx, row in enumerate(table_buffer):
                padded = [f" {(row[c].replace('**', '').replace('*', '') if c < len(row) else ''):<{widths[c]}} " for c in range(n_cols)]
                tag = "table_hdr" if r_idx == 0 else ("table_even" if r_idx % 2 == 1 else "table_odd")
                self.text_widget.insert(tk.END, "│" + "│".join(padded) + "│\n", (tag,))
            self.text_widget.insert(tk.END, "\n")
            table_buffer.clear()

        for line in md_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("<!-- PLOT:") and stripped.endswith("-->"):
                _flush_table()
                key = stripped[len("<!-- PLOT:"):-3].strip()
                if key in figures and figures[key] is not None:
                    self._embed_plot_in_text(key, figures[key])
                continue
            if stripped.startswith("```"):
                _flush_table(); in_code = not in_code; continue
            if in_code:
                self.text_widget.insert(tk.END, f"  {line}\n", ("code_block",)); continue
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    table_buffer.append(cells)
                continue
            _flush_table()
            if stripped.startswith("# "): self.text_widget.insert(tk.END, f"{stripped[2:]}\n", ("h1",))
            elif stripped.startswith("## "): self.text_widget.insert(tk.END, f" {stripped[3:]}\n", ("h2",))
            elif stripped.startswith("### "): self.text_widget.insert(tk.END, f"{stripped[4:]}\n", ("h3",))
            elif stripped.startswith("- "): self._insert_styled_spans(f"• {stripped[2:]}\n", base_tag="bullet")
            else: self._insert_styled_spans(f"{line}\n")

        _flush_table()
        self.text_widget.config(state="disabled")

    def _insert_styled_spans(self, text: str, base_tag: Optional[str] = None) -> None:
        pos = 0
        base_tags = (base_tag,) if base_tag else ()
        for m in re.finditer(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*)", text):
            if m.start() > pos:
                self.text_widget.insert(tk.END, text[pos:m.start()], base_tags)
            tok = m.group(0)
            if tok.startswith("**"): self.text_widget.insert(tk.END, tok[2:-2], (*base_tags, "bold"))
            elif tok.startswith("`"): self.text_widget.insert(tk.END, tok[1:-1], (*base_tags, "code"))
            else: self.text_widget.insert(tk.END, tok[1:-1], (*base_tags, "italic"))
            pos = m.end()
        if pos < len(text):
            self.text_widget.insert(tk.END, text[pos:], base_tags)

    def _embed_plot_in_text(self, key: str, fig: Any) -> None:
        try:
            photo = tk.PhotoImage(master=self.text_widget, data=figure_to_png_bytes(fig, dpi=95))
            self._photo_refs.append(photo)
        except Exception:
            return
        card = tk.Frame(self.text_widget, bg="#FFFFFF", highlightbackground=PALETTE["border"], highlightthickness=1, padx=8, pady=6)
        toolbar = tk.Frame(card, bg="#FFFFFF")
        toolbar.pack(fill=tk.X, pady=(0, 4))
        tk.Label(toolbar, text=PLOT_CAPTIONS.get(key, "Diagnostic Plot"), bg="#FFFFFF", fg=PALETTE["text_secondary"], font=self.fonts["small_bold"]).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="💾 Save Image...", style="Small.TButton", command=lambda k=key: self.prompt_save_figure(k)).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="✏ Edit Plot...", style="Small.TButton", command=lambda k=key: self.prompt_edit_figure(k)).pack(side=tk.RIGHT, padx=(0, 6))
        img_lbl = tk.Label(card, image=photo, bg="#FFFFFF", bd=0)
        img_lbl.pack()
        menu = tk.Menu(card, tearoff=0)
        menu.add_command(label="Edit Plot...", command=lambda k=key: self.prompt_edit_figure(k))
        menu.add_command(label="Save Image As...", command=lambda k=key: self.prompt_save_figure(k))
        img_lbl.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        img_lbl.bind("<Double-Button-1>", lambda e, k=key: self.prompt_edit_figure(k))
        for w in (card, toolbar, img_lbl):
            w.bind("<MouseWheel>", lambda e: self.text_widget.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._embedded_frames.append(card)
        self.text_widget.insert(tk.END, "\n")
        self.text_widget.window_create(tk.END, window=card, padx=4, pady=4)
        self.text_widget.insert(tk.END, "\n\n")

    def get_markdown_text(self) -> str: return self._markdown_source
    def get_html_text(self) -> str: return self._html_source
