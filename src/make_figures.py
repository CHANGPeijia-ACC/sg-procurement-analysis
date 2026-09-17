"""Generate all figures used in the README / notebook from the cleaned data.

Run: python src/make_figures.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
import pandas as pd

from analysis import (
    aggregate_by_tender,
    benford_mad,
    concentration_by_group,
    threshold_window_counts,
    top_suppliers,
    yearly_trend,
)
from plotting import set_style

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "gebiz_cleaned.csv"
FIG_DIR = ROOT / "outputs" / "figures"

THRESHOLDS = {"Tender threshold (S$90,000)": 90000}


def fig_concentration(df: pd.DataFrame) -> None:
    res = concentration_by_group(df, ["agency"], min_awards=10).head(12).sort_values("hhi")
    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(res["agency"], res["hhi"])
    ax.axvline(2500, color="#d97706", linestyle="--", linewidth=1, label="High concentration (HHI 2,500)")
    ax.set_xlabel("HHI (amount-weighted, 0-10,000)")
    ax.set_title("Supplier concentration by agency (top 12 by HHI, min. 10 awards)")
    ax.legend(loc="lower right", fontsize=8)
    for bar, n in zip(bars, res["n_suppliers"]):
        ax.text(bar.get_width() + 60, bar.get_y() + bar.get_height() / 2, f"{n} suppliers", va="center", fontsize=8, color="#555")
    fig.savefig(FIG_DIR / "concentration_by_agency.png")
    plt.close(fig)


def fig_amount_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots()
    vals = df.loc[df["awarded_amt"] > 0, "awarded_amt"]
    bins = np.logspace(np.log10(vals.min()), np.log10(vals.max()), 60)
    ax.hist(vals, bins=bins, color="#2563eb", alpha=0.85)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for label, t in THRESHOLDS.items():
        ax.axvline(t, color="#dc2626", linestyle="--", linewidth=1)
        ax.text(t, ax.get_ylim()[1] * 0.6, f" {label}", rotation=90, fontsize=8, color="#dc2626", va="top")
    ax.set_xlabel("Awarded amount (S$, log scale)")
    ax.set_ylabel("Number of awards (log scale)")
    ax.set_title("Distribution of award amounts (row level)")
    fig.savefig(FIG_DIR / "amount_distribution.png")
    plt.close(fig)


def fig_threshold_zoom(df: pd.DataFrame, threshold: float = 90000, lo: float = 81000, hi: float = 99000, bin_width: float = 1000) -> None:
    tenders = aggregate_by_tender(df)
    panels = [
        ("Row level (award line items)", df),
        ("Tender level (ETT tenders, summed)", tenders[tenders["procurement_type"] == "ETT"]),
    ]
    bins = np.arange(lo, hi + bin_width, bin_width)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for ax, (title, data) in zip(axes, panels):
        vals = data.loc[(data["awarded_amt"] >= lo) & (data["awarded_amt"] < hi), "awarded_amt"]
        ax.hist(vals, bins=bins, color="#2563eb", alpha=0.85, edgecolor="white")
        ax.axvline(threshold, color="#dc2626", linestyle="--", linewidth=1.5)
        w = threshold_window_counts(data, [threshold], window_pct=0.02).iloc[0]
        ax.set_title(
            f"{title}\n+/-2% window: {int(w.n_just_below)} below, {int(w.n_just_above)} above, one-sided p = {w.p_more_below:.3f}",
            fontsize=10,
        )
        ax.set_xlabel(r"Awarded amount (S\$, S\$1,000 bins)")
        ax.set_xticks(np.arange(lo + 1000, hi, 2000))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:.0f}k"))
    axes[0].set_ylabel("Count")
    fig.suptitle(f"Awards near the S${threshold:,.0f} tender threshold (dashed line)", fontsize=12)
    fig.savefig(FIG_DIR / f"threshold_zoom_{int(threshold)}.png")
    plt.close(fig)


def _benford_title(label: str, r: dict) -> str:
    return (f"{label} vs. Benford's law, row level, amounts >= S${r['min_amount']:,.0f} (n = {r['n']:,})\n"
            f"MAD {r['mad']:.5f} (Nigrini band: {r['band']}), chi-square p = {r['p_value']:.3g}")


def fig_benford(df: pd.DataFrame, min_amount: float = 10) -> None:
    r = benford_mad(df["awarded_amt"], digits=1, min_amount=min_amount)
    t = r["table"]
    fig, ax = plt.subplots()
    width = 0.38
    x = t.index.to_numpy()
    ax.bar(x - width / 2, t["observed"] * 100, width, label="Observed", color="#2563eb")
    ax.bar(x + width / 2, t["expected"] * 100, width, label="Benford (expected)", color="#94a3b8")
    ax.set_xticks(x)
    ax.set_xlabel("First digit")
    ax.set_ylabel("% of awards")
    ax.set_title(_benford_title("First digit", r), fontsize=10)
    ax.legend()
    fig.savefig(FIG_DIR / "benford_test.png")
    plt.close(fig)


def fig_benford_two_digits(df: pd.DataFrame, min_amount: float = 10) -> None:
    r = benford_mad(df["awarded_amt"], digits=2, min_amount=min_amount)
    t = r["table"]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(t.index, t["observed"] * 100, width=0.8, label="Observed", color="#2563eb")
    ax.plot(t.index, t["expected"] * 100, color="#dc2626", linewidth=1.5, label="Benford (expected)")
    ax.set_xticks(np.arange(10, 100, 10))
    ax.set_xlim(9, 100)
    ax.set_xlabel("First two digits")
    ax.set_ylabel("% of awards")
    ax.set_title(_benford_title("First two digits", r), fontsize=10)
    ax.legend()
    fig.savefig(FIG_DIR / "benford_two_digits.png")
    plt.close(fig)


def fig_yearly_trend(df: pd.DataFrame) -> None:
    trend = yearly_trend(df)
    fig, ax1 = plt.subplots()
    ax1.bar(trend["fiscal_year"], trend["total_amt"] / 1e9, color="#2563eb", alpha=0.8, label="Total awarded (S$B)")
    ax1.set_ylabel("Total awarded (S$ billion)")
    ax2 = ax1.twinx()
    ax2.plot(trend["fiscal_year"], trend["n_awards"], color="#dc2626", marker="o", label="Number of awards")
    ax2.set_ylabel("Number of awards")
    ax2.grid(False)
    ax1.set_title("Government procurement spend and award volume by fiscal year")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    fig.savefig(FIG_DIR / "yearly_trend.png")
    plt.close(fig)


def fig_top_suppliers(df: pd.DataFrame) -> None:
    top = top_suppliers(df, 10).sort_values("total_amt")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["supplier_name"], top["total_amt"] / 1e9, color="#2563eb")
    ax.set_xlabel("Total awarded, FY2021-FY2025 (S$ billion)")
    ax.set_title("Top 10 suppliers by total awarded amount")
    fig.savefig(FIG_DIR / "top_suppliers.png")
    plt.close(fig)


if __name__ == "__main__":
    set_style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH, low_memory=False)

    fig_concentration(df)
    fig_amount_distribution(df)
    fig_threshold_zoom(df)
    fig_benford(df)
    fig_benford_two_digits(df)
    fig_yearly_trend(df)
    fig_top_suppliers(df)
    print(f"Figures written to {FIG_DIR}")
