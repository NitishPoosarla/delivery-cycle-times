"""06-software-delivery — collect engineering-workflow data via the public GitHub API.

Sample: pandas-dev/pandas closed issues + all issues in their state at fetch time.
Unauthenticated REST (rate-limited); the script pages until it has ~2,000 items.
"""
from pathlib import Path
import time

import requests

PROJECT = Path(__file__).resolve().parent.parent
REPO = "pandas-dev/pandas"
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "portfolio/1.0"}


def main() -> None:
    dest = PROJECT / "data" / "raw" / "github_issues.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[cache] {dest.name} present ({dest.stat().st_size:,} bytes)")
        return
    got = []
    page = 1
    while len(got) < 2000 and page <= 10:   # deep pagination caps out on GitHub; 1k pages is enough
        r = requests.get(
            f"https://api.github.com/repos/{REPO}/issues",
            params={"state": "all", "per_page": 100, "page": page,
                    "sort": "created", "direction": "desc"},
            headers=HEADERS, timeout=60)
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        got.extend(items)
        page += 1
        time.sleep(1.2)
    lines = []
    for it in got:
        lines.append({
            "number": it["number"],
            "title": it["title"],
            "state": it["state"],
            "created_at": it["created_at"],
            "closed_at": it["closed_at"],
            "comments": it["comments"],
            "labels": [l["name"] for l in it["labels"]],
            "author_association": it["author_association"],
        })
    dest.write_text("\n".join(__import__("json").dumps(x) for x in lines), encoding="utf-8")
    print(f"[save] {dest} ({len(lines)} issues)")


if __name__ == "__main__":
    main()
