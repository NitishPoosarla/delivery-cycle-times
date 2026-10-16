"""06-software-delivery — 03_dashboard.py — single-file engineering delivery dashboard."""
from pathlib import Path
import json
import sys

import pandas as pd
import plotly.graph_objects as go

_shared_root = Path(__file__).resolve().parent
while _shared_root != _shared_root.parent and not (_shared_root / "shared").is_dir():
    _shared_root = _shared_root.parent
sys.path.insert(0, str(_shared_root))  # callable from repo root or standalone checkout
from shared.dashboard import build_dashboard   # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"


def main() -> None:
    kpis = json.loads((OUT / "kpis.json").read_text())
    lab = pd.read_csv(OUT / "seg_labels.csv", index_col=0)
    cb = pd.read_csv(OUT / "seg_cycle_comments.csv", index_col=0)
    issues = pd.read_csv(PROJECT / "data" / "processed" / "issues.csv", parse_dates=["created_at", "closed_at"])

    fig_ct = go.Figure(go.Histogram(x=issues.dropna(subset=["cycle_days"]).cycle_days.clip(0, 120),
                                    marker_color="#134e5e", nbinsx=40))
    fig_ct.update_layout(xaxis_title="Open→close (days)", yaxis_title="Issues")

    labx = lab.sort_values("issues")
    fig_lab = go.Figure(go.Bar(y=labx.index, x=labx.issues, orientation="h", marker_color="#0e7490",
                               text=labx.med_cycle.round(1), textposition="outside",
                               texttemplate="%{text}d median"))
    fig_lab.update_layout(yaxis=dict(title=""))

    fig_cb = go.Figure(go.Bar(x=[str(c) for c in cb.index], y=cb["median"], marker_color="#d97706"))
    fig_cb.update_layout(xaxis_title="Comments per issue", yaxis_title="Median cycle (days)")

    build_dashboard(
        str(PROJECT / "dashboard" / "index.html"),
        title="Engineering Delivery Analytics — Flow & Triage",
        subtitle=("What predicts cycle time and what the triage process should change. "
                  "Sampled from pandas-dev/pandas via the public GitHub API. Verified in Python."),
        badges=["Software", "DORA-style flow", "Backlog health", "LLM narration"],
        kpis=[
            {"label": "Issues sampled", "value": f"{kpis['issues']:,}"},
            {"label": "Median cycle", "value": f"{kpis['median_cycle_days']:.1f}d", "note": f"P90: {kpis['p90_cycle_days']:.0f}d"},
            {"label": "Open >180d", "value": f"{kpis['share_open_over_180d']:.0%}"},
            {"label": "Labeled - median open age", "value": f"{kpis['median_open_age_labeled']:.0f}d",
             "note": f"vs {kpis['median_open_age_unlabeled']:.0f}d unlabeled"},
            {"label": "Median chatter", "value": str(kpis["median_comments"])},
        ],
        figures=[
            {"title": "Cycle time distribution", "fig": fig_ct},
            {"title": "Label mix vs speed", "sub": "issue count (bars), median days (labels)", "fig": fig_lab},
            {"title": "Chatter vs velocity", "fig": fig_cb},
        ],
        recommendations=[
            "Label-on-arrival triage SLA: unlabeled issues age far longer — the cheapest flow fix available.",
            "Cap consenus-threads: issues with 10+ comments resolve slowest; route them to a decision-owner protocol.",
            "Track a DORA-flavored trio weekly: median cycle, P90 cycle, share of open >180d — publish internally.",
            "Use this baseline to justify AI triage: pre-classification by an LLM needs *this chart* as its comparison point.",
        ],
        footer=("Data: GitHub REST API, pandas-dev/pandas (public). AI narrates verified metrics only "
                "and could serve as triage assistant — evaluated against this baseline."),
    )
    print("dashboard written")


if __name__ == "__main__":
    main()
