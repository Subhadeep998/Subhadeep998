#!/usr/bin/env python3
"""Refresh the 'Live from my radars' block in the profile README.

Pulls today's top item from each daily radar (their committed data files)
and star counts for every open-knowledge hub. Standard library only.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

OWNER = "Subhadeep998"
HUBS = ["Global-Company-Radar", "Law-Firm-Radar", "Science-Research-Radar", "AI-Developer-Docs-Hub",
        "Awesome-Biotechnology", "Awesome-AI-Learning", "Open-Biology-Handbook", "India-Development-Dashboard"]
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")


def get_json(url, api=False):
    headers = {"User-Agent": "profile-live"}
    if api and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.loads(r.read())


def raw(repo, path):
    return get_json(f"https://raw.githubusercontent.com/{OWNER}/{repo}/main/{path}")


def esc(s, n=110):
    s = re.sub(r"<[^>]+>", "", s or "").replace("|", "\\|").replace("[", "(").replace("]", ")").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def newest_news(repo, noun):
    cache = raw(repo, "data/news-cache.json")
    best = None
    for slug, v in cache.items():
        for n in v.get("latest", [])[:1]:
            if not best or n["date"] > best[0]["date"]:
                best = (n, slug)
    if not best:
        return None
    n, slug = best
    name = slug.replace("-", " ").title()
    return f"[{esc(n['title'])}]({n['link']}) — _{name}_"


def newest_paper():
    c = raw("Science-Research-Radar", "data/cache.json")
    rows = [(r["date"], j, r) for j, lst in c.get("journals", {}).items() for r in lst[:1]]
    if not rows:
        return None
    d, j, r = max(rows, key=lambda t: t[0])
    return f"[{esc(r['title'])}]({r['link']}) — _{j}_"


def newest_release():
    c = raw("AI-Developer-Docs-Hub", "data/releases.json")
    rows = [(r[0]["date"], repo, r[0]) for repo, r in c.items() if r and r[0].get("date")]
    if not rows:
        return None
    d, repo, r = max(rows, key=lambda t: t[0])
    return f"[{repo} **{esc(r['tag'], 40)}**]({r['url']}) — _released {d}_"


def newest_india():
    d = get_json(f"https://raw.githubusercontent.com/{OWNER}/India-Development-Dashboard/main/docs/data/dashboard.json")
    items = [n for t in d.get("tabs", []) for n in t.get("pib", [])[:1]]
    if not items:
        return None
    n = max(items, key=lambda x: x.get("date", ""))
    return f"[{esc(n['title'])}]({n['link']}) — _PIB_"


def main():
    items = [
        ("🏢", "Company Radar", "Global-Company-Radar", lambda: newest_news("Global-Company-Radar", "company")),
        ("⚖️", "Law Firm Radar", "Law-Firm-Radar", lambda: newest_news("Law-Firm-Radar", "firm")),
        ("🔬", "Science Radar", "Science-Research-Radar", newest_paper),
        ("🤖", "AI Docs Hub", "AI-Developer-Docs-Hub", newest_release),
        ("🇮🇳", "India Dashboard", "India-Development-Dashboard", newest_india),
    ]
    rows = ["| Radar | Today's top item |", "|:--|:--|"]
    for emoji, label, repo, fn in items:
        try:
            got = fn()
        except Exception as exc:
            print(f"[skip] {label}: {exc}", file=sys.stderr)
            got = None
        rows.append(f"| {emoji} [**{label}**](https://github.com/{OWNER}/{repo}) | {got or '_Updating…_'} |")

    stars = 0
    for repo in HUBS:
        try:
            stars += get_json(f"https://api.github.com/repos/{OWNER}/{repo}", api=True).get("stargazers_count", 0)
        except Exception as exc:
            print(f"[stars] {repo}: {exc}", file=sys.stderr)
    today = dt.date.today().strftime("%d %b %Y")
    lead = f"⭐ {stars} stars across 8 open-knowledge hubs" if stars >= 10 else "8 open-knowledge hubs · 5 refresh daily"
    block = ("\n".join(rows) + f"\n\n<sub>{lead} · updated automatically {today} · all free and open</sub>\n")

    s = open(README, encoding="utf-8").read()
    s2 = re.sub(r"<!-- live:start -->.*?<!-- live:end -->", "<!-- live:start -->\n" + block + "<!-- live:end -->", s, flags=re.S)
    if s2 != s:
        open(README, "w", encoding="utf-8").write(s2)
        print("README updated.")
    else:
        print("No change.")


if __name__ == "__main__":
    main()
