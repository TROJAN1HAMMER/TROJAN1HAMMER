#!/usr/bin/env python3
"""
Dynamic GitHub Activity & Telemetry Updater for Harshith B (TROJAN1HAMMER)
Fetches real public events and recent repositories using the GitHub API,
and cleanly updates the generated section in README.md without modifying
any manual content.
"""

import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

USERNAME = "TROJAN1HAMMER"
START_MARKER = "<!-- DYNAMIC_ACTIVITY:START -->"
END_MARKER = "<!-- DYNAMIC_ACTIVITY:END -->"

def fetch_json(url: str, token: str = None) -> any:
    headers = {"User-Agent": "TROJAN1HAMMER-Profile-Updater"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP error fetching {url}: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def format_relative_time(date_str: str) -> str:
    try:
        event_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - event_time
        days = delta.days
        seconds = delta.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if days == 0:
            if hours == 0:
                return f"{max(1, minutes)}m ago"
            return f"{hours}h ago"
        elif days == 1:
            return "1d ago"
        elif days < 30:
            return f"{days}d ago"
        elif days < 365:
            months = days // 30
            return f"{months}mo ago"
        else:
            return f"{days // 365}y ago"
    except Exception:
        return "recently"

def get_recent_activity(token: str = None) -> str:
    events = fetch_json(f"https://api.github.com/users/{USERNAME}/events/public?per_page=15", token)
    if not events or not isinstance(events, list):
        return None

    rows = []
    seen = set()
    count = 0

    for event in events:
        if count >= 5:
            break
        event_type = event.get("type")
        repo_name = event.get("repo", {}).get("name", "")
        repo_url = f"https://github.com/{repo_name}"
        created_at = format_relative_time(event.get("created_at", ""))
        
        display_name = repo_name.replace(f"{USERNAME}/", "")
        
        action_label = "Update"
        
        if event_type == "PushEvent":
            action_label = "Commit"
            commits = event.get("payload", {}).get("commits", [])
            commit_count = len(commits)
            if commits:
                first_msg = commits[0].get("message", "").split("\n")[0]
                if len(first_msg) > 60:
                    first_msg = first_msg[:57] + "..."
                desc = f"Pushed {commit_count} commit{'s' if commit_count > 1 else ''} to <a href='{repo_url}'><b>{display_name}</b></a> (<code>{first_msg}</code>)"
            else:
                desc = f"Pushed updates to <a href='{repo_url}'><b>{display_name}</b></a>"
        elif event_type == "CreateEvent":
            action_label = "Create"
            ref_type = event.get("payload", {}).get("ref_type", "resource")
            ref_name = event.get("payload", {}).get("ref", "")
            if ref_type == "repository":
                desc = f"Created repository <a href='{repo_url}'><b>{display_name}</b></a>"
            elif ref_type == "branch":
                desc = f"Created branch <code>{ref_name}</code> on <a href='{repo_url}'><b>{display_name}</b></a>"
            elif ref_type == "tag":
                desc = f"Created tag <code>{ref_name}</code> on <a href='{repo_url}'><b>{display_name}</b></a>"
            else:
                desc = f"Created {ref_type} on <a href='{repo_url}'><b>{display_name}</b></a>"
        elif event_type == "WatchEvent":
            action_label = "Star"
            desc = f"Starred repository <a href='{repo_url}'><b>{repo_name}</b></a>"
        elif event_type == "ForkEvent":
            action_label = "Fork"
            desc = f"Forked repository <a href='{repo_url}'><b>{repo_name}</b></a>"
        elif event_type == "PullRequestEvent":
            action = event.get("payload", {}).get("action", "opened")
            pr_num = event.get("payload", {}).get("number", "")
            action_label = "PR"
            desc = f"{action.capitalize()} PR #{pr_num} on <a href='{repo_url}'><b>{display_name}</b></a>"
        elif event_type == "IssuesEvent":
            action = event.get("payload", {}).get("action", "opened")
            issue_num = event.get("payload", {}).get("issue", {}).get("number", "")
            action_label = "Issue"
            desc = f"{action.capitalize()} issue #{issue_num} on <a href='{repo_url}'><b>{display_name}</b></a>"
        elif event_type == "ReleaseEvent":
            tag = event.get("payload", {}).get("release", {}).get("tag_name", "")
            action_label = "Release"
            desc = f"Published release <code>{tag}</code> on <a href='{repo_url}'><b>{display_name}</b></a>"
        else:
            continue

        key = (event_type, repo_name, desc[:30])
        if key in seen:
            continue
        seen.add(key)

        rows.append(f"""    <tr>
      <td width="80" align="center"><code>{action_label}</code></td>
      <td>{desc}</td>
      <td width="90" align="right"><sub>{created_at}</sub></td>
    </tr>""")
        count += 1

    if not rows:
        return None

    table = "<table width=\"100%\">\n" + "\n".join(rows) + "\n  </table>"
    return table

def update_readme():
    token = os.environ.get("GITHUB_TOKEN")
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    
    if not os.path.exists(readme_path):
        print(f"README file not found at {readme_path}")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print("Markers not found in README.md, skipping dynamic update.")
        return

    recent_table = get_recent_activity(token)
    if not recent_table:
        print("Could not fetch real events or no new public events found.")
        return

    pattern = re.compile(f"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}", re.DOTALL)
    replacement = f"{START_MARKER}\n\n{recent_table}\n\n{END_MARKER}"
    
    new_content = pattern.sub(replacement, content)
    
    if new_content != content:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md successfully updated with latest engineering telemetry.")
    else:
        print("README.md is already up to date.")

if __name__ == "__main__":
    update_readme()
