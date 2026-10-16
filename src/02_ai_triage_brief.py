"""06-software-delivery — 02_ai_triage_brief.py — measured AI engineering-culture brief."""
from pathlib import Path
import csv
import json
import sys

_shared_root = Path(__file__).resolve().parent
while _shared_root != _shared_root.parent and not (_shared_root / "shared").is_dir():
    _shared_root = _shared_root.parent
sys.path.insert(0, str(_shared_root))  # callable from repo root or standalone checkout
from shared import llm   # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "outputs"


def main() -> None:
    kpis = json.loads((OUT / "kpis.json").read_text())
    with open(OUT / "seg_labels.csv") as f:
        labels = list(csv.DictReader(f))
    with open(OUT / "seg_cycle_comments.csv") as f:
        chatter = list(csv.DictReader(f))
    drivers = {
        "Backlog age is the debt": (f"{kpis['share_open_over_180d']:.0%} of issues are open-equivalents "
                                    f"older than 180 days; unlabeled issues sit far longer than labeled ones."),
        "Triage pays in speed": ("Labeling correlates with faster cycle; label mix shows what work actually "
                                 "gets consumed."),
        "Chatter slows flow": ("More comments → longer resolution; consensus-building is real cost."),
    }
    prompt = f"""You are briefing an engineering leadership team (DORA-flavored). Use ONLY verified metrics.
Deliver: (1) two-sentence health read, (2) ranked process actions, (3) metrics to instrument next.
Metrics: {json.dumps({**kpis, "labels": labels, "chatter": chatter}, indent=1)}"""
    md = llm.write_insights(str(OUT / "insights.md"), "Engineering delivery health", kpis, drivers, prompt)
    print(md[:900])


if __name__ == "__main__":
    main()
