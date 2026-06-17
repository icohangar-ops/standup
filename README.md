# Standup — AI-Native Daily Standup for Anna

> Built for the [Anna AI-Native App Hackathon](https://dorahacks.io/hackathon/2204/detail) — DoraHacks #2204

**One mention. Your whole day, summarized.**

`#standup` pulls real developer activity from GitHub, Slack, and Calendar, runs it through deterministic analysis, and produces a structured standup — no typing, no guessing, no fabricating.

```
#standup

🎤 Standup — cubiczan — 2026-06-17

**What I Did**
• 2 feature commits (feat: add user authentication flow)
• 1 bugfix commit: fix: resolve login redirect loop
• 1 refactor commit: refactor: extract auth middleware
• Merged 1 PR: Fix login redirect

**What I'm Doing**
• PR: Add OAuth2 support (my-app)
• Issue: Setup CI pipeline

**Blockers**
• PR 'Add OAuth2 support' — no reviewers assigned
• Issue 'Update dependencies' is blocked

📊 5 commits · 1 PR merged · 1 PR open · 2 blocker(s)
```

---

## The Problem

Every developer standup suffers from the same four failures:

1. **Recall bias** — you forget half of what you did yesterday, especially after context-switching across repos, branches, and code reviews. The human brain is not a git log.

2. **Vagueness** — "worked on some stuff" and "pushed some commits" are not useful. Without structure, standups become rituals that produce zero signal.

3. **Blocker hiding** — blockers go unmentioned until they've already cost the team a day or more. Developers don't want to look stuck, so they soft-pedal dependencies and review bottlenecks.

4. **Time waste** — 15 minutes of meeting time for 30 seconds of actual information. Multiply by 5-10 developers and you're burning 1-2.5 hours of engineering time daily on a ritual that could be asynchronous.

The root cause is clear: standups rely on **human memory and honesty**, two things that are notoriously unreliable under deadline pressure. Every existing "AI standup" tool just wraps an LLM around a free-text prompt — which introduces hallucination and still requires the developer to type what they remember. That's not automation. That's formatting.

## The Solution

Standup replaces human recall with **actual data from the tools developers already use**, and replaces LLM guesswork with **deterministic analysis** that produces consistent, honest output every time.

The key insight: Anna's runtime already has built-in integrations for GitHub, Slack, and Calendar. Standup doesn't need to authenticate to anything or build its own API clients. It uses Anna's existing tools to gather data, then applies a dedicated analysis engine (the `standup-tool` Executa) to classify, structure, and detect problems — things an LLM alone cannot do reliably.

This is not a chatbot that asks "what did you do today?" It's a workflow that **pulls data, runs analysis, and delivers a report**. The user says one word: `#standup`.

## How It Works

```
User types: #standup

Anna runtime:
  1. Activates Standup app (system_prompt_addendum)
  2. standup-playbook Skill guides the agent's workflow
  3. Agent calls Anna's built-in GitHub tool → commits, PRs, issues (last 24h)
  4. Agent calls Anna's built-in Slack tool → @mentions, urgent threads
  5. Agent calls Anna's built-in Calendar tool → today's meetings
  6. Agent calls standup-tool Executa (format_standup) with all collected data
  7. standup-tool classifies commits, detects blockers, produces structured output
  8. Agent formats the standup using playbook guidelines
  9. User gets a clean, data-backed standup in under 5 seconds
```

The workflow is fully automated. Zero manual input. Zero hallucination risk — the analysis is deterministic Python code, not LLM inference.

## Architecture

Standup is a native **Anna App** that demonstrates the platform's core primitives: Tool Executas, Skill Executas, and the App manifest that orchestrates them together.

### 1. Tool Executa: `standup-tool` (Python, zero dependencies)

A JSON-RPC 2.0 plugin over stdin/stdout that performs the deterministic analysis an LLM cannot:

| Tool | Purpose |
|------|---------|
| `format_standup` | Classifies commits into 8 categories (feature, bugfix, refactor, testing, docs, merge, release, infra), summarizes PR merge/review activity, detects blockers from labels, comments, and message patterns, and produces a structured standup with metrics |
| `detect_blockers` | Focused blocker scanner — examines PR comments, issue labels, Slack messages, and review statuses for 12+ blocking signals, returns severity-ranked deduplicated list |
| `weekly_digest` | Aggregates daily standups into a weekly team report: velocity metrics, burndown indicators, top themes, daily breakdown table, and actionable recommendations |
| `health_score` | Computes a team health score (0-100, letter grade A-D) from four weighted dimensions: consistency (20%), blocker health (30%), activity level (30%), velocity trend (20%) |

The tool is **pure Python stdlib** — no pip install, no virtual environment, no container. Ships as a single 430-line file.

### 2. Skill Executa: `standup-playbook` (SKILL.md)

A declarative methodology document that acts as "prompt-as-code" for the Anna agent:

- **Data gathering protocol** — exactly which Anna built-in tools to call, what data to request, and in what order
- **Tool invocation guide** — how to structure `format_standup` and `detect_blockers` calls with proper parameter schemas
- **Output formatting rules** — the exact standup template, tone guidelines (concise, action verbs, 30-second read), and special case handling (no activity, all blockers, new team members, weekends)
- **Extended formats** — weekly digest table format and health report structure

The Skill ensures the agent behaves consistently regardless of which LLM model Anna routes to.

### 3. Anna App Manifest

Bundles both Executas with a `system_prompt_addendum` that activates the standup workflow on `#standup`. The manifest declares `standup-tool` as a required Tool Executa and `standup-playbook` as a required Skill Executa.

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Anna Runtime                      │
│                                                      │
│  User: #standup                                      │
│       │                                              │
│       ▼                                              │
│  ┌─────────────┐    ┌──────────────────────────┐     │
│  │  standup-    │    │  Anna Built-in Tools      │     │
│  │  playbook    │───▶│  • GitHub (commits,PRs,  │     │
│  │  (Skill)     │    │    issues)                │     │
│  │              │    │  • Slack (mentions,       │     │
│  │  Guides the  │    │    messages)              │     │
│  │  agent's     │    │  • Calendar (meetings)    │     │
│  │  workflow    │    └──────────┬───────────────┘     │
│  └─────────────┘               │                      │
│                                │ raw activity data    │
│                                ▼                      │
│                     ┌─────────────────────┐          │
│                     │   standup-tool      │          │
│                     │   (Tool Executa)    │          │
│                     │                     │          │
│                     │  • format_standup   │          │
│                     │  • detect_blockers  │          │
│                     │  • weekly_digest    │          │
│                     │  • health_score     │          │
│                     └─────────┬───────────┘          │
│                               │                      │
│                               ▼                      │
│                     Structured standup output         │
│                     (What I Did / Doing / Blockers)   │
└─────────────────────────────────────────────────────┘
```

## Blocker Detection Engine

Blocker detection is the highest-value feature — it catches problems that developers naturally underreport. The engine scans 12+ signal patterns across three data sources:

**From PRs:**
- Labels: `blocked`, `needs-review`, `waiting`, `hold`
- Comment keywords: "blocked on", "waiting on", "depends on", "can't merge", "held up", "stuck"
- Review status: `no_reviewers`, `changes_requested`

**From Issues:**
- Labels: `blocked`, `needs-review`, `waiting`, `hold`, `urgent`, `critical`

**From Slack:**
- Message keywords: "blocked", "waiting on you", "urgent", "asap", "when can you"

All signals are deduplicated, tagged with source and severity (high/medium), and sorted so the most critical blockers appear first. This means a developer who types `#standup` will surface blockers they might have otherwise mentioned only in next week's retrospective.

## Why Anna?

Standup is purpose-built for Anna's architecture. Here's why it only works as an Anna App:

1. **Built-in integrations eliminate auth hell** — Anna already connects to GitHub, Slack, and Calendar. Standup doesn't need OAuth flows, API tokens, or permission screens. The user installs the app and it works immediately.

2. **Executas enable real computation** — A pure LLM cannot reliably classify commits, detect blockers from comment patterns, or compute health scores. The Tool Executa does deterministic analysis. The Skill Executa ensures consistent behavior. The App manifest wires them together. This is the Anna pattern.

3. **Human-in-the-loop by default** — Anna's runtime supports human review before actions. While Standup is read-only (it never modifies anything), the architecture means it could be extended to act on blockers (e.g., "assign a reviewer to PR #42") with human approval.

4. **Prompt-as-code methodology** — The SKILL.md playbook is not "instructions for an LLM." It's a versionable, testable methodology document that governs agent behavior. Change the playbook, change the output — no code deploy needed.

## Technical Details

- **Protocol**: JSON-RPC 2.0 over stdio (Anna Executa specification)
- **Language**: Python 3.10+ (stdlib only — zero external dependencies)
- **Skill Format**: SKILL.md with YAML frontmatter (Anna Skill Executa specification)
- **App Format**: JSON manifest v1 (Anna App specification)
- **Size**: 430 lines of Python + 110 lines of SKILL.md + 1 JSON manifest
- **Startup**: Instant (no imports to resolve, no containers to spin up)

## Running Locally

```bash
# Verify the Executa is healthy
echo '{"jsonrpc":"2.0","method":"health","id":0}' | python3 executa/standup-tool/standup_tool.py
# → {"jsonrpc":"2.0","id":0,"result":{"status":"ready"}}

# Get the tool manifest
echo '{"jsonrpc":"2.0","method":"describe","id":1}' | python3 executa/standup-tool/standup_tool.py

# Run a full standup analysis
python3 -c "
import json, subprocess
req = {
    'jsonrpc': '2.0', 'id': 2, 'method': 'invoke',
    'params': {
        'tool': 'format_standup',
        'arguments': {
            'activities': {
                'commits': [
                    {'message': 'feat: add OAuth2 flow', 'repo': 'my-app', 'timestamp': '2026-06-17T10:00:00Z'},
                    {'message': 'fix: resolve redirect loop', 'repo': 'my-app', 'timestamp': '2026-06-17T11:00:00Z'},
                    {'message': 'refactor: extract auth middleware', 'repo': 'my-app', 'timestamp': '2026-06-17T12:00:00Z'}
                ],
                'pull_requests': [
                    {'title': 'Add OAuth2 support', 'status': 'open', 'repo': 'my-app', 'labels': ['blocked'], 'comments': [{'author': 'teammate', 'body': 'Blocked on auth server migration', 'timestamp': '2026-06-17T09:00:00Z'}], 'review_status': 'no_reviewers'},
                    {'title': 'Fix redirect loop', 'status': 'merged', 'repo': 'my-app', 'labels': ['bug'], 'comments': [], 'review_status': 'approved'}
                ],
                'issues': [
                    {'title': 'Setup CI pipeline', 'status': 'In Progress', 'labels': [], 'assignee': 'me'}
                ],
                'messages': [
                    {'channel': 'team-dev', 'text': '@you review PR #42 when you can?', 'timestamp': '2026-06-17T08:00:00Z', 'is_mention': True}
                ]
            },
            'team_config': {'username': 'developer', 'blocker_labels': ['blocked', 'needs-review', 'waiting']}
        }
    }
}
p = subprocess.run(['python3', 'executa/standup-tool/standup_tool.py'], input=json.dumps(req), capture_output=True, text=True)
print(json.dumps(json.loads(p.stdout), indent=2))
"
```

## Publishing to Anna

1. Register as a developer at [anna.partners/developer](https://anna.partners/developer)
2. Publish `standup-tool` as a Tool Executa (Python, local or binary distribution)
3. Publish `standup-playbook` as a Skill Executa (Markdown upload)
4. Create the `standup` Anna App using the manifest in `app/manifest.json`
5. Submit for review

## Project Structure

```
standup-anna/
├── executa/
│   └── standup-tool/
│       └── standup_tool.py          # Python JSON-RPC Executa (4 tools, zero deps, 430 lines)
├── skill/
│   └── standup-playbook/
│       └── SKILL.md                 # Declarative standup methodology (110 lines)
├── app/
│   └── manifest.json                # Anna App manifest (v1)
├── LICENSE
└── README.md
```

## Impact

Standup eliminates the four fundamental failures of developer standups:

| Problem | Before | After |
|---------|--------|-------|
| Recall bias | "I think I worked on auth stuff" | "3 feature commits, 1 bugfix, 1 refactor — all classified from git history" |
| Vagueness | "pushed some commits" | "feat: add OAuth2 flow · fix: resolve redirect loop · refactor: extract auth middleware" |
| Blocker hiding | "Nothing blocking me" (lie) | "PR 'Add OAuth2 support' — no reviewers assigned · Issue 'Update dependencies' is blocked" |
| Time waste | 15-min synchronous meeting | 5-second async mention: `#standup` |

For a 5-person team, that's 12.5 hours per week reclaimed — not from eliminating standups, but from making them actually work.

---

**Event**: Anna AI-Native App Hackathon — [DoraHacks #2204](https://dorahacks.io/hackathon/2204/detail)
**Team**: Cubiczan
**Category**: Productivity

Built with [Anna Developer Platform](https://anna.partners/developers).