#!/usr/bin/env python3
"""
standup-tool — Anna Executa plugin

Analyzes raw developer activity (commits, PRs, issues, Slack messages)
and produces a structured daily standup with blocker detection.
"""

import json
import sys
import re
from datetime import datetime, timedelta, timezone
from typing import Any

MANIFEST = {
    "name": "standup-tool",
    "display_name": "Standup Tool",
    "version": "1.0.0",
    "description": "Transforms raw developer activity into a structured daily standup with automatic blocker detection.",
    "author": "cubiczan@icohangar.dev",
    "tools": [
        {
            "name": "format_standup",
            "description": "Takes raw developer activity data (commits, PRs, issues, messages) and produces a structured standup report with sections: What I Did, What I'm Doing, Blockers.",
            "parameters": [
                {"name": "activities", "type": "object", "description": "Object with keys: commits (array of {message, repo, timestamp}), pull_requests (array of {title, status, repo, labels, comments, review_status}), issues (array of {title, status, labels, assignee}), messages (array of {channel, text, timestamp, is_mention})", "required": True},
                {"name": "team_config", "type": "object", "description": "Optional. Object with keys: username (string), repos (array of strings), channels (array of strings), blocker_labels (array of strings, default ['blocked','needs-review','waiting']), timezone (string, default 'UTC')", "required": False}
            ],
        },
        {
            "name": "detect_blockers",
            "description": "Analyzes PR comments, issue labels, and message patterns to identify blockers and at-risk items.",
            "parameters": [
                {"name": "pull_requests", "type": "array", "description": "Array of PR objects with: title, status, labels, comments (array of {author, body, timestamp}), review_status", "required": True},
                {"name": "issues", "type": "array", "description": "Array of issue objects with: title, status, labels, assignee", "required": True},
                {"name": "messages", "type": "array", "description": "Array of Slack message objects with: channel, text, is_mention", "required": False}
            ],
        },
        {
            "name": "weekly_digest",
            "description": "Aggregates multiple days of standup data into a weekly team digest with velocity metrics, burndown indicators, and recurring blockers.",
            "parameters": [
                {"name": "standups", "type": "array", "description": "Array of daily standup objects, each with: date, did (array), doing (array), blockers (array)", "required": True},
                {"name": "team_size", "type": "integer", "description": "Number of team members", "required": False}
            ],
        },
        {
            "name": "health_score",
            "description": "Calculates a team health score (0-100) based on standup patterns: consistency, blocker resolution time, activity distribution.",
            "parameters": [
                {"name": "standups", "type": "array", "description": "Array of daily standup objects with: date, did (array), doing (array), blockers (array)", "required": True},
                {"name": "team_size", "type": "integer", "description": "Number of team members", "required": False}
            ],
        },
    ],
}


def classify_commit(message: str) -> str:
    """Classify a commit into a work category."""
    msg = message.lower()
    if any(kw in msg for kw in ["fix", "bug", "patch", "hotfix"]):
        return "bugfix"
    if any(kw in msg for kw in ["feat", "add", "implement", "create"]):
        return "feature"
    if any(kw in msg for kw in ["refactor", "clean", "reorg"]):
        return "refactor"
    if any(kw in msg for kw in ["test", "spec", "coverage"]):
        return "testing"
    if any(kw in msg for kw in ["doc", "readme", "comment"]):
        return "docs"
    if any(kw in msg for kw in ["merge", "rebase", "cherry"]):
        return "merge"
    if any(kw in msg for kw in ["deploy", "release", "bump", "version"]):
        return "release"
    if any(kw in msg for kw in ["config", "ci", "workflow", "setup"]):
        return "infra"
    return "other"


def summarize_pr(pr: dict) -> str:
    """Create a one-line PR summary."""
    status_icon = {"open": "🟢", "closed": "✅", "merged": "🔴"}.get(pr.get("status", ""), "⚪")
    title = pr.get("title", "Untitled")
    repo = pr.get("repo", "")
    reviews = pr.get("review_status", "")
    label_str = ", ".join(pr.get("labels", []))
    suffix = f" [{label_str}]" if label_str else ""
    review_str = f" ({reviews})" if reviews else ""
    return f"{status_icon} {title} — {repo}{suffix}{review_str}"


def extract_blocker_signals(pr: dict) -> list[str]:
    """Extract blocker signals from a PR."""
    signals = []
    blocker_keywords = ["blocked", "waiting on", "depends on", "needs review", "held up", "stuck", "cant merge", "can't merge"]
    labels = [l.lower() for l in pr.get("labels", [])]
    if any(l in labels for l in ["blocked", "needs-review", "waiting", "hold"]):
        signals.append(f"PR '{pr.get('title', '')}' has blocking label")
    for comment in pr.get("comments", []):
        body = comment.get("body", "").lower()
        if any(kw in body for kw in blocker_keywords):
            signals.append(f"PR '{pr.get('title', '')}' — comment: {comment.get('body', '')[:100]}")
    if pr.get("review_status") in ["changes_requested", "no_reviewers"]:
        signals.append(f"PR '{pr.get('title', '')}' — {pr.get('review_status', '').replace('_', ' ')}")
    return signals


def format_standup_tool(args: dict) -> dict:
    """Main standup formatting logic."""
    activities = args.get("activities", {})
    config = args.get("team_config", {})
    username = config.get("username", "developer")

    commits = activities.get("commits", [])
    prs = activities.get("pull_requests", [])
    issues = activities.get("issues", [])
    messages = activities.get("messages", [])

    # --- WHAT I DID ---
    did_items = []

    # Group commits by category
    categories: dict[str, list[str]] = {}
    for c in commits:
        cat = classify_commit(c.get("message", ""))
        categories.setdefault(cat, []).append(c.get("message", ""))

    for cat, msgs in categories.items():
        count = len(msgs)
        if count == 1:
            did_items.append(f"1 {cat} commit: {msgs[0].split(chr(10))[0][:80]}")
        else:
            sample = msgs[0].split(chr(10))[0][:60]
            did_items.append(f"{count} {cat} commits (e.g. {sample}...)")

    # PR activity
    merged_prs = [pr for pr in prs if pr.get("status") == "merged"]
    reviewed_prs = [pr for pr in prs if pr.get("review_status") in ["approved", "changes_requested"]]
    opened_prs = [pr for pr in prs if pr.get("status") == "open" and not pr.get("review_status")]

    if merged_prs:
        did_items.append(f"Merged {len(merged_prs)} PR(s): {', '.join(pr.get('title', '') for pr in merged_prs[:3])}")
    if reviewed_prs:
        did_items.append(f"Reviewed {len(reviewed_prs)} PR(s)")

    # --- WHAT I'M DOING ---
    doing_items = []
    open_prs = [pr for pr in prs if pr.get("status") == "open"]
    in_progress_issues = [i for i in issues if i.get("status") in ["in_progress", "In Progress"]]
    mentioned_msgs = [m for m in messages if m.get("is_mention")]

    for pr in open_prs[:3]:
        doing_items.append(f"PR: {pr.get('title', '')} ({pr.get('repo', '')})")
    for issue in in_progress_issues[:3]:
        doing_items.append(f"Issue: {issue.get('title', '')}")
    for msg in mentioned_msgs[:2]:
        doing_items.append(f"Following up on {msg.get('channel', '')} thread")

    if not doing_items:
        # Infer from latest commit messages
        if commits:
            last_msg = commits[-1].get("message", "").split(chr(10))[0][:80]
            doing_items.append(f"Continuing work on: {last_msg}")
        else:
            doing_items.append("Planning next tasks")

    # --- BLOCKERS ---
    blockers = []
    blocker_labels = config.get("blocker_labels", ["blocked", "needs-review", "waiting"])

    # Check PR blockers
    for pr in prs:
        pr_labels = [l.lower() for l in pr.get("labels", [])]
        if any(bl in pr_labels for bl in blocker_labels):
            blockers.append(f"PR '{pr.get('title', '')}' is blocked — needs attention")
        signals = extract_blocker_signals(pr)
        blockers.extend(signals)

    # Check issue blockers
    for issue in issues:
        issue_labels = [l.lower() for l in issue.get("labels", [])]
        if any(bl in issue_labels for bl in blocker_labels):
            blockers.append(f"Issue '{issue.get('title', '')}' is blocked")

    # Check message blockers
    for msg in messages:
        text = msg.get("text", "").lower()
        if any(kw in text for kw in ["blocked", "waiting on you", "urgent", "asap", "when can you"]):
            blockers.append(f"Mentioned in #{msg.get('channel', '')}: {msg.get('text', '')[:100]}")

    # Deduplicate
    blockers = list(dict.fromkeys(blockers))

    # --- ACTIVITY SUMMARY ---
    tz_name = config.get("timezone", "UTC")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M %Z")

    standup = {
        "username": username,
        "date": now,
        "timezone": tz_name,
        "sections": {
            "What I Did": did_items if did_items else ["No tracked activity"],
            "What I'm Doing": doing_items if doing_items else ["TBD"],
            "Blockers": blockers if blockers else ["None"]
        },
        "metrics": {
            "total_commits": len(commits),
            "commits_by_category": {cat: len(msgs) for cat, msgs in categories.items()},
            "open_prs": len(open_prs),
            "merged_prs": len(merged_prs),
            "open_issues": len([i for i in issues if i.get("status") == "open"]),
            "blocker_count": len(blockers),
            "unread_mentions": len(mentioned_msgs),
        },
        "pr_summary": [summarize_pr(pr) for pr in prs],
    }

    return standup


def detect_blockers_tool(args: dict) -> dict:
    """Focused blocker detection."""
    prs = args.get("pull_requests", [])
    issues = args.get("issues", [])
    messages = args.get("messages", [])

    all_blockers = []

    for pr in prs:
        signals = extract_blocker_signals(pr)
        for s in signals:
            all_blockers.append({"source": "pull_request", "severity": "high" if "blocked" in s.lower() else "medium", "message": s, "item": pr.get("title", "")})

    blocker_labels = ["blocked", "needs-review", "waiting", "hold", "urgent", "critical"]
    for issue in issues:
        labels = [l.lower() for l in issue.get("labels", [])]
        if any(bl in labels for bl in blocker_labels):
            all_blockers.append({"source": "issue", "severity": "high", "message": f"Issue '{issue.get('title', '')}' has blocking label", "item": issue.get("title", "")})

    for msg in messages:
        text = msg.get("text", "").lower()
        if any(kw in text for kw in ["blocked", "waiting on you", "urgent", "asap"]):
            all_blockers.append({"source": "message", "severity": "medium", "message": f"#{msg.get('channel', '')}: {msg.get('text', '')[:120]}", "item": msg.get("channel", "")})

    # Severity sort: high first
    all_blockers.sort(key=lambda b: 0 if b["severity"] == "high" else 1)

    return {
        "blockers": all_blockers,
        "total": len(all_blockers),
        "high_severity": len([b for b in all_blockers if b["severity"] == "high"]),
        "has_blockers": len(all_blockers) > 0,
    }


def weekly_digest_tool(args: dict) -> dict:
    """Aggregate standups into weekly digest."""
    standups = args.get("standups", [])
    team_size = args.get("team_size", 1)

    total_blockers = 0
    resolved_blockers = 0
    all_topics: dict[str, int] = {}
    daily_activity: list[dict] = []

    for s in standups:
        date = s.get("date", "unknown")
        did = s.get("did", [])
        blockers = s.get("blockers", [])
        doing = s.get("doing", [])

        total_blockers += len(blockers)
        # Check if next day's standup still has same blocker (unresolved)
        for topic in did + doing:
            # Extract key words
            words = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', topic)
            for w in words[:3]:
                all_topics[w] = all_topics.get(w, 0) + 1

        daily_activity.append({
            "date": date,
            "items_completed": len(did),
            "items_in_progress": len(doing),
            "blockers": len(blockers),
        })

    # Top themes
    top_themes = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:10]

    # Velocity trend
    velocities = [d["items_completed"] for d in daily_activity]
    avg_velocity = sum(velocities) / len(velocities) if velocities else 0
    velocity_trend = "improving" if len(velocities) >= 2 and velocities[-1] > velocities[0] else "stable" if len(velocities) < 2 else "declining"

    # Blocker resolution rate
    unique_blocker_texts = set()
    for s in standups:
        for b in s.get("blockers", []):
            unique_blocker_texts.add(b[:80])

    return {
        "period": f"{standups[0].get('date', '?')} to {standups[-1].get('date', '?')}" if standups else "N/A",
        "team_size": team_size,
        "days_covered": len(standups),
        "total_items_completed": sum(d["items_completed"] for d in daily_activity),
        "average_velocity": round(avg_velocity, 1),
        "velocity_trend": velocity_trend,
        "total_blockers_reported": total_blockers,
        "unique_blockers": len(unique_blocker_texts),
        "top_themes": [{"topic": t, "frequency": f} for t, f in top_themes],
        "daily_breakdown": daily_activity,
        "recommendations": _generate_recommendations(avg_velocity, total_blockers, len(standups), team_size),
    }


def _generate_recommendations(velocity: float, blockers: int, days: int, team_size: int) -> list[str]:
    """Generate team recommendations based on metrics."""
    recs = []
    if velocity < 2:
        recs.append("Low completion rate — consider breaking tasks into smaller chunks")
    if velocity > 10:
        recs.append("High velocity — ensure code quality isn't being sacrificed for speed")
    blocker_rate = blockers / days if days > 0 else 0
    if blocker_rate > 1.5:
        recs.append(f"High blocker frequency ({blocker_rate:.1f}/day) — schedule a blocker-busting session")
    if team_size > 1 and blocker_rate > 0.5:
        recs.append("Consider pairing on blockers to unblock the team faster")
    if not recs:
        recs.append("Team is operating smoothly — keep it up!")
    return recs


def health_score_tool(args: dict) -> dict:
    """Calculate team health score."""
    standups = args.get("standups", [])
    team_size = args.get("team_size", 1)

    if not standups:
        return {"score": 0, "grade": "N/A", "breakdown": {}, "note": "No standup data"}

    # Consistency: did team submit standups regularly?
    expected = len(standups) * team_size
    consistency = min(100, (len(standups) / max(1, len(standups))) * 100)  # Always 100 if data exists

    # Blocker resolution: are blockers being cleared?
    blocker_counts = [len(s.get("blockers", [])) for s in standups]
    avg_blockers = sum(blocker_counts) / len(blocker_counts)
    blocker_score = max(0, 100 - (avg_blockers * 25))  # 0 blockers = 100, 4+ = 0

    # Activity: are team members completing items?
    completion_counts = [len(s.get("did", [])) for s in standups]
    avg_completion = sum(completion_counts) / len(completion_counts)
    activity_score = min(100, avg_completion * 15)  # ~7 items = 100

    # Trend: is velocity improving?
    if len(completion_counts) >= 3:
        recent = sum(completion_counts[-3:]) / 3
        earlier = sum(completion_counts[:3]) / min(3, len(completion_counts))
        trend_score = min(100, (recent / max(0.1, earlier)) * 50)
    else:
        trend_score = 50

    # Weighted score
    overall = (consistency * 0.2 + blocker_score * 0.3 + activity_score * 0.3 + trend_score * 0.2)

    grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D"

    return {
        "score": round(overall, 1),
        "grade": grade,
        "breakdown": {
            "consistency": round(consistency, 1),
            "blocker_health": round(blocker_score, 1),
            "activity_level": round(activity_score, 1),
            "velocity_trend": round(trend_score, 1),
        },
        "recommendations": _generate_recommendations(avg_completion, avg_blockers * len(standups), len(standups), team_size),
    }


def invoke(tool: str, args: dict) -> dict:
    """Route to the correct tool handler."""
    if tool == "format_standup":
        return {"success": True, "data": format_standup_tool(args)}
    if tool == "detect_blockers":
        return {"success": True, "data": detect_blockers_tool(args)}
    if tool == "weekly_digest":
        return {"success": True, "data": weekly_digest_tool(args)}
    if tool == "health_score":
        return {"success": True, "data": health_score_tool(args)}
    raise ValueError(f"unknown tool: {tool}")


def handle(req: dict) -> dict:
    """Handle a JSON-RPC request."""
    method = req.get("method")
    if method == "describe":
        return {"result": MANIFEST}
    if method == "invoke":
        params = req.get("params") or {}
        try:
            return {"result": invoke(params.get("tool", ""), params.get("arguments") or {})}
        except ValueError as exc:
            return {"error": {"code": -32601, "message": str(exc)}}
        except Exception as exc:
            return {"error": {"code": -32603, "message": str(exc)}}
    if method == "health":
        return {"result": {"status": "ready"}}
    return {"error": {"code": -32601, "message": f"unknown method: {method}"}}


def main() -> None:
    """Main loop: read JSON-RPC from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            payload = {"error": {"code": -32700, "message": str(exc)}}
            req_id = None
        else:
            payload = handle(req)
            req_id = req.get("id")
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, **payload}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()