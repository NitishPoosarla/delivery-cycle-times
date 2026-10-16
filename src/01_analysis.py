"""06-software-delivery — 01_analysis.py

Engineering delivery analytics: open→close cycle time, label taxonomy,
community engagement, DORA-flavored flow metrics.

Outputs: processed issues, kpis.json, segments, charts.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

_shared_root = Path(__file__).resolve().parent
while _shared_root != _shared_root.parent and not (_shared_root / "shared").is_dir():
    _shared_root = _shared_root.parent
sys.path.insert(0, str(_shared_root))  # callable from repo root or standalone checkout
from shared.utils import mpl_setup, save_png, save_json   # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"
mpl_setup()


def main() -> None:
    (PROJECT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_json(PROJECT / "data" / "raw" / "github_issues.jsonl", lines=True)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_convert(None)
    df["closed_at"] = pd.to_datetime(df["closed_at"]).dt.tz_convert(None)
    df["cycle_days"] = (df["closed_at"] - df["created_at"]).dt.total_seconds() / 86400
    df.loc[df["state"] != "closed", "cycle_days"] = np.nan
    df["n_labels"] = df["labels"].str.len()
    df["open_age_days"] = (pd.Timestamp.now() - df["created_at"]).dt.total_seconds() / 86400

    closed = df[df.state == "closed"]
    kpis = {
        "issues": int(len(df)),
        "closed": int(len(closed)),
        "open": int(len(df) - len(closed)),
        "median_cycle_days": round(float(closed.cycle_days.median()), 2),
        "p90_cycle_days": round(float(closed.cycle_days.quantile(.9)), 2),
        "median_comments": round(float(df.comments.median()), 1),
        "share_open_over_180d": round(float((df.loc[df.state == "open", "open_age_days"] > 180).mean()), 4),
        "top_label": "",
    }
    # label taxonomy (top labels)
    lab = df.explode("labels").groupby("labels").agg(
        issues=("number", "count"), med_cycle=("cycle_days", "mean")).sort_values("issues", ascending=False).head(12)
    kpis["top_label"] = str(lab.index[0]) if len(lab) else ""
    lab.round(2).to_csv(OUT / "seg_labels.csv")

    # triage quality proxy: labeled vs unlabeled open issues
    qp = df[df.state == "open"]
    band = qp.assign(labeled=qp.n_labels > 0).groupby("labeled").open_age_days.median()
    kpis["median_open_age_labeled"] = round(float(band.get(True, np.nan)), 1)
    kpis["median_open_age_unlabeled"] = round(float(band.get(False, np.nan)), 1)

    # cycle time vs comment volume (engagement vs velocity)
    df["comment_band"] = pd.cut(df.comments, [-1, 0, 2, 10, 10**9], labels=["0", "1-2", "3-10", "10+"])
    cb = df[df.state == "closed"].groupby("comment_band").cycle_days.agg(["median", "count"]).round(2)
    cb.to_csv(OUT / "seg_cycle_comments.csv")

    df.round(2).to_csv(PROJECT / "data" / "processed" / "issues.csv", index=False)
    save_json(kpis, OUT / "kpis.json")

    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.hist(closed.cycle_days.clip(0, 120), bins=40, color="#134e5e")
    ax.axvline(closed.cycle_days.median(), color="#e2584c", ls="--",
               label=f"median {closed.cycle_days.median():.1f}d")
    ax.set_xlabel("Open → close (days)"); ax.legend()
    ax.set_title("Cycle time distribution — where delivery actually lands")
    save_png(fig, OUT / "charts" / "cycle_time.png")

    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax2 = ax.twinx()
    ax.bar(lab.index.astype(str), lab.issues, color="#0e7490", alpha=.8)
    ax2.plot(lab.index.astype(str), lab.med_cycle, "o", color="#e2584c")
    ax.tick_params(axis="x", rotation=60)
    ax.set_ylabel("Issue count")
    ax2.set_ylabel("Median cycle (days)", color="#e2584c")
    ax.set_title("Label mix — theme vs flow speed")
    save_png(fig, OUT / "charts" / "labels.png")

    cb2 = cb.reset_index()
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(cb2.comment_band.astype(str), cb2["median"], color="#d97706")
    ax.set_xlabel("Comments on issue"); ax.set_ylabel("Median cycle (days)")
    ax.set_title("Chatter vs velocity: engagement slows resolution")
    save_png(fig, OUT / "charts" / "chatter.png")
    print(json.dumps(kpis, indent=2))


if __name__ == "__main__":
    main()
