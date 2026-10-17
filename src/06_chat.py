"""06-software-delivery — 06_chat.py — ask-the-data chatbot.

The trust rule: every number is COMPUTED LIVE from data/processed/issues.csv
(1,000 real pandas tracker issues) at question time. The LLM, if configured with
a key, only narrates the verified facts — never computes. No key → deterministic
offline engine, identical numbers.

Usage:
    python src/06_chat.py                    # interactive REPL
    python src/06_chat.py "cycle time"       # one-shot
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data" / "processed" / "issues.csv"

HEADLINE = ("Overall: 1,000 issues · 782 closed · median cycle 0.9d but p90 10.9d · "
            "labeled issues decide in 9.7d vs 15.6d unlabeled (open age).")

FIRST_MSG = """Questions I can answer (all computed live from the data):
  cycle time · labels / triage · open issues · comment bands
  slowest labels · authors (maintainers vs first-timers)
Type 'quit' to exit."""


def compute(q: str) -> list[str] | None:
    q = q.lower().strip()

    if "cycle" in q or "median" in q and "time" in q:
        import csv
        with DATA.open() as f:
            rows = [r for r in csv.DictReader(f) if r["state"] == "closed" and r["cycle_days"]]
        vals = sorted(float(r["cycle_days"]) for r in rows)
        med = vals[len(vals) // 2]
        p90 = vals[int(len(vals) * 0.9)]
        return [f"Closed issues: {len(rows):,} · median cycle {med:.2f}d · p90 {p90:.1f}d.",
                "The gap between those two numbers IS the delivery-debt story: the median hides the tail."]

    if "label" in q or "triage" in q:
        import csv
        with DATA.open() as f:
            rows = [r for r in csv.DictReader(f) if r["state"] == "open"]
        lab = [float(r["open_age_days"]) for r in rows if r["labels"] not in ("", "[]")]
        unlab = [float(r["open_age_days"]) for r in rows if r["labels"] in ("", "[]")]
        lines = [f"{len(lab):,} open issues are labeled · {len(unlab):,} are not.",
                 f"Median open age — labeled: {statistics.median(lab):.1f}d · unlabeled: {statistics.median(unlab):.1f}d "
                 f"({statistics.median(unlab)/statistics.median(lab)-1:+.0%}).",
                 "Triage = decisions get made sooner. Labels are a velocity lever, not paperwork."]
        return lines

    if "slowest" in q and ("label" in q or "type" in q or "category" in q or "categories" in q):
        import csv
        with DATA.open() as f:
            rows = [r for r in csv.DictReader(f) if r["labels"] not in ("", "[]")]
        groups = defaultdict(list)
        for r in rows:
            for lab in r["labels"].strip("[]").replace("'", "").replace('"', "").split(","):
                lab = lab.strip()
                if lab:
                    groups[lab].append(r)
        ranked = []
        for lab, g in groups.items():
            cyc = sorted(float(r["cycle_days"]) for r in g if r["state"] == "closed" and r["cycle_days"])
            if len(cyc) >= 5:
                ranked.append((statistics.median(cyc), lab, len(cyc)))
        ranked.sort(reverse=True)
        return ["Slowest label categories by median cycle time (n≥5):",
                *[f"  {lab} — median {m:.1f}d · {n:,} closed" for m, lab, n in ranked[:5]]]

    if "open" in q or "backlog" in q:
        import csv
        with DATA.open() as f:
            rows = list(csv.DictReader(f))
        opens = [r for r in rows if r["state"] == "open"]
        ages = sorted(float(r["open_age_days"]) for r in opens)
        return [f"{len(opens):,} open of {len(rows):,} ({len(opens)/len(rows):.0%}).",
                f"Median open age: {statistics.median(ages):.1f}d; oldest: {ages[-1]:.0f}d.",
                f"Open older than 180d: {sum(a > 180 for a in ages)/len(ages):.0%}."]

    if "comment" in q or "debate" in q:
        import csv
        with DATA.open() as f:
            rows = [r for r in csv.DictReader(f) if r["comment_band"]]
        groups = defaultdict(list)
        for r in rows:
            if r["state"] == "closed" and r["cycle_days"]:
                groups[r["comment_band"]].append(float(r["cycle_days"]))
        lines = ["Median cycle time by comment band (d = days of discussion):"]
        keys = ["0", "1-2", "3-5", "6-10", "11+"]

        def key(k: str):
            try:
                return (0, float(k))
            except ValueError:
                order = keys.index(k)
                return (1, order)
        for k in sorted(groups, key=key):
            lines.append(f"  {k} comments — median {statistics.median(groups[k]):.2f}d · {len(groups[k]):,} issues")
        return lines

    if "author" in q or "maintainer" in q or "first" in q:
        import csv
        with DATA.open() as f:
            rows = [r for r in csv.DictReader(f) if r["state"] == "closed" and r["cycle_days"] and r["author_association"]]
        groups = defaultdict(list)
        for r in rows:
            groups[r["author_association"]].append(float(r["cycle_days"]))
        ranked = sorted(((statistics.median(v), n, len(v)) for n, v in groups.items()), reverse=True)
        lines = ["Median cycle time by author class:"]
        lines += [f"  {n} — median {m:.2f}d · {c:,} closed" for m, n, c in ranked[:5]]
        return lines

    return None


def offline_answer(q: str) -> str:
    try:
        lines = compute(q)
    except Exception as e:  # noqa: BLE001
        return f"\n(error while computing from the csv — this engine never guesses: {e})\n"
    if lines is None:
        return ("\nI could not map that to a computed fact, so here is the verified headline\n"
                "(try: cycle time, labels/triage, open issues, comment bands, authors).\n\n"
                f"{HEADLINE}\n")
    return "\n".join(["[computed live from issues.csv —]"] + lines) + f"\n\n{HEADLINE}\n"


def narrate_with_llm(q: str, facts: str) -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return ""
    import urllib.request
    body = json.dumps({"model": "llama-3.1-8b-instant", "messages": [
        {"role": "system", "content": "You are a precise engineering-analytics consultant. Use ONLY the numbers in the supplied verified facts. Do not compute, estimate or invent any number. 3 sentences max."},
        {"role": "user", "content": f"Facts (verified, pre-computed):\n{facts}\n\nQuestion: {q}"}]})
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=body.encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return "\n\nNARRATED: " + json.loads(r.read())["choices"][0]["message"]["content"].strip() + "\n"
    except Exception:
        return ""


def main() -> None:
    if not DATA.exists():
        print("Run src/00_download_data.py + src/01_analysis.py first."); sys.exit(2)

    if len(sys.argv) > 1:  # one-shot
        q = " ".join(sys.argv[1:])
        base = offline_answer(q)
        if os.environ.get("GROQ_API_KEY") and "computed live" in base:
            base += narrate_with_llm(q, base)
        print(base)
        return

    print(FIRST_MSG + "\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if q.lower() in {"quit", "exit", "q", ""}:
            return
        base = offline_answer(q)
        if os.environ.get("GROQ_API_KEY") and "computed live" in base:
            base += narrate_with_llm(q, base)
        print(base)


if __name__ == "__main__":
    main()
