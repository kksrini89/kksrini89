#!/usr/bin/env python3
"""Regenerate the LIVE_STATS block in README.md from the GitHub API.

Text, not images: the Action runs this daily and commits the diff,
so the numbers are real markdown — nothing to 503, works in every theme.

Runs unauthenticated (60 req/hr) or with GITHUB_TOKEN (5k req/hr).
"""
import collections
import datetime
import json
import os
import re
import sys
import urllib.request

USER = "kksrini89"
FEATURED = ["artifactsweep", "dontbemichael", "rn-recurrly"]
README = "README.md"
BEGIN = "<!--LIVE_STATS:START-->"
END = "<!--LIVE_STATS:END-->"
API = "https://api.github.com"


def gh(path):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "live-stats"},
    )
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    return json.load(urllib.request.urlopen(req, timeout=30))


def all_repos():
    out, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&page={page}")
        if not batch:
            return out
        out += batch
        page += 1


def months(iso):
    return datetime.date.fromisoformat(iso[:10]).strftime("%b %Y")


def main():
    user = gh(f"/users/{USER}")
    repos = all_repos()
    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in own)
    langs = collections.Counter(r["language"] for r in own if r["language"])
    total = sum(langs.values()) or 1
    yrs = (datetime.date.today() - datetime.date.fromisoformat(user["created_at"][:10])).days // 365

    rows = []
    for name in FEATURED:
        try:
            r = gh(f"/repos/{USER}/{name}")
        except Exception as e:
            print(f"featured repo {name}: {e}", file=sys.stderr)
            continue
        desc = (r.get("description") or "").strip()
        lic = (r.get("license") or {}).get("spdx_id", "")
        lic = f" · {lic}" if lic and lic != "NOASSERTION" else ""
        rows.append(
            f"| [**{r['name']}**](https://github.com/{USER}/{r['name']}) "
            f"| {desc}{lic} "
            f"| {r['stargazers_count']} | {r['forks_count']} | {r['open_issues_count']} "
            f"| {months(r['pushed_at'])} |"
        )

    top = " · ".join(f"{k} {round(v / total * 100)}%" for k, v in langs.most_common(6))

    block = f"""{BEGIN}
<sub>🛠️ **{len(own)} own repos** &nbsp;·&nbsp; 🍴 **{len(repos) - len(own)} contributed / forked** &nbsp;·&nbsp; ⭐ **{stars} stars earned** &nbsp;·&nbsp; 👥 **{user['followers']} followers** &nbsp;·&nbsp; 📅 **on GitHub {yrs} yrs**</sub>

| Project | What | ★ | ⑂ | Issues | Last push |
|---|---|---|---|---|---|
{chr(10).join(rows)}

<sub>top languages · {top}</sub><br>
<sub>⚙️ numbers refreshed daily by a GitHub Action — real text, no image services</sub>
{END}"""

    src = open(README).read()
    if BEGIN not in src:
        sys.exit(f"{BEGIN} marker not found in {README}")
    new = re.sub(f"{BEGIN}.*?{END}", block, src, flags=re.S)
    if new != src:
        open(README, "w").write(new)
        print("README.md updated")
    else:
        print("already up to date")


if __name__ == "__main__":
    main()
