"""06 — banner: slate flow strip, 12x cycle-time gap."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

k = json.loads((Path(__file__).resolve().parents[1] / "outputs" / "kpis.json").read_text())

fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
ax.set_xlim(0, 12); ax.set_ylim(0, 6.75); ax.axis("off")
fig.patch.set_facecolor("#23262b")

ax.text(0.5, 6.05, "MEDIAN 0.9 DAYS. P90 10.9. THE TAIL IS THE WORK.",
        fontsize=17.5, fontweight="bold", color="#e9ecef")
ax.text(0.5, 5.5, "1,000 real issues, pandas-dev tracker, fetched timestamped from the public API",
        fontsize=11, color="#9099a2")

# cycle-time strip
x0, x1, y = 0.7, 11.3, 3.4
ax.plot([x0, x1], [y, y], color="#5a6470", lw=2)
for frac, lbl, big in [(0.06, "median", f"{k['median_cycle_days']:.2f}d"),
                       (1.0, "p90", f"{k['p90_cycle_days']:.1f}d")]:
    x = x0 + frac * (x1 - x0)
    ax.plot([x, x], [y - 0.25, y + 0.55], color="#62b0c9", lw=3)
    ax.text(x, y + 0.8, lbl, fontsize=10, color="#9099a2", ha="center")
    ax.text(x, y - 0.62, big, fontsize=16, fontweight="bold", color="#e9ecef", ha="center")

ax.text(0.7, 2.35, "labeled issues clear in ~9.7d median open age vs ~15.6d unlabeled —",
        fontsize=11.5, color="#e9ecef")
ax.text(0.7, 1.85, "labeling-on-arrival is the cheapest flow fix on the board.",
        fontsize=11.5, color="#e9ecef")

ax.text(0.7, 0.85, "correlational read: more debate (comments) → slower cycle; consensus costs days.",
        fontsize=10.5, color="#9099a2")
fig.savefig(Path(__file__).resolve().parents[1] / "outputs" / "banner.png",
            dpi=100, facecolor=fig.get_facecolor())
print("banner written")
