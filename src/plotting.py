"""Shared matplotlib configuration for all figures in this project."""

import matplotlib.pyplot as plt

# CJK fallback fonts are listed defensively (see notes.md — the raw data is
# pure ASCII, so this is not currently load-bearing) so a stray CJK label in
# a notebook cell doesn't render as tofu boxes.
FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial",
    "DejaVu Sans",
]

PALETTE = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2"]


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": FONT_CANDIDATES,
            "axes.unicode_minus": False,
            "figure.dpi": 110,
            "figure.figsize": (9, 5),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.axisbelow": True,
            "axes.prop_cycle": plt.cycler(color=PALETTE),
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
        }
    )
