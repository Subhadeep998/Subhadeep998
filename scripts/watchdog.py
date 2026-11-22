#!/usr/bin/env python3
"""Daily health check of every automation across the open-knowledge repos.

If any workflow's latest finished run failed, open (or update) one issue in
this repo titled 'Automation alert' — GitHub emails the owner. When all are
healthy again, the issue is closed automatically.
"""
import json
import os
import sys
import urllib.request

OWNER = "Subhadeep998"
HOME = f"{OWNER}/{OWNER}"
REPOS = ["Subhadeep998", "Global-Company-Radar", "Law-Firm-Radar", "Science-Research-Radar",
         "AI-Developer-Docs-Hub", "Awesome-Biotechnology", "Awesome-AI-Learning", "Open-Biology-Handbook"]
TITLE = "⚠️ Automation alert"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path, method="GET", body=None):
    req = urllib.request.Request(f"https://api.github.com/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "watchdog",
                                          **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def main():
    problems, checked = [], 0
    for repo in REPOS:
        try:
            workflows = api(f"repos/{OWNER}/{repo}/actions/workflows").get("workflows", [])
        except Exception as exc:
            problems.append(f"- **{repo}**: could not read workflows ({exc})")
            continue
        for wf in workflows:
            if wf.get("state") != "active":
                if wf.get("state", "").startswith("disabled"):
                    problems.append(f"- **{repo} → {wf['name']}** is **disabled** ({wf['state']}). "
                                    f"[Open Actions](https://github.com/{OWNER}/{repo}/actions)")
                continue
            runs = api(f"repos/{OWNER}/{repo}/actions/workflows/{wf['id']}/runs?status=completed&per_page=1").get("workflow_runs", [])
            if not runs:
                continue
            checked += 1
            run = runs[0]
            if run.get("conclusion") == "failure":
                problems.append(f"- **{repo} → {wf['name']}** failed on {run['created_at'][:10]} — "
                                f"[see the log]({run['html_url']})")

    open_issues = api(f"repos/{HOME}/issues?state=open&per_page=100")
    alert = next((i for i in open_issues if i.get("title") == TITLE and "pull_request" not in i), None)

    if problems:
        body = ("Some automations need attention:\n\n" + "\n".join(problems) +
                "\n\nMost one-off failures fix themselves on the next scheduled run (a news or research source was "
                "briefly down). If the same item appears several days in a row, open the log and ask for help.\n\n"
                f"_Checked {checked} workflows across {len(REPOS)} repositories._")
        if alert:
            api(f"repos/{HOME}/issues/{alert['number']}/comments", "POST", {"body": body})
        else:
            api(f"repos/{HOME}/issues", "POST", {"title": TITLE, "body": body})
        print("\n".join(problems))
    else:
        if alert:
            api(f"repos/{HOME}/issues/{alert['number']}/comments", "POST",
                {"body": f"✅ All {checked} automations are healthy again. Closing."})
            api(f"repos/{HOME}/issues/{alert['number']}", "PATCH", {"state": "closed"})
        print(f"All {checked} workflows healthy.")


if __name__ == "__main__":
    sys.exit(main())
