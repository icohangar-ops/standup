# Standup

> AI-Native Daily Standup for Anna — [DoraHacks #2204](https://dorahacks.io/hackathon/2204/detail)

**One mention. Your whole day, summarized.**

Type `#standup` and Anna pulls your actual commits, PRs, issues, Slack mentions, and calendar meetings from the tools you already use — then runs deterministic analysis to produce a structured, data-backed standup. No typing. No guessing. No fabricating.

---

## The Problem

Developer standups are a daily ritual that fails at every step:

**Recall bias.** You context-switched across 4 repos, reviewed 3 PRs, fixed a flaky test, and helped a teammate debug a race condition. By standup time, you remember maybe half of it. The human brain is not a git log — expecting developers to accurately recall 8 hours of fragmented work is a design flaw.

**Vagueness.** "Worked on some stuff." "Pushed some commits." "Made progress on the feature." These are the most common standup answers, and they carry zero information. Without structure, standups produce noise, not signal.

**Blocker hiding.** Developers don't want to look stuck. So they say "nothing blocking me" while their PR has had no reviewer for two days, their issue depends on a blocked API migration, and three Slack threads are waiting on their input. Blockers go unmentioned until they've already burned the team.

**Time waste.** A 5-person team spending 15 minutes each in standup burns 12.5 hours per week on a ritual that generates 30 seconds of useful information per person. That's a 99.3% waste ratio.

Every "AI standup" tool on the market today fails the same way: they wrap an LLM around a free-text prompt. You still have to type what you remember. The LLM still hallucinates. You've just hired an AI to format your bad data. That's not automation — that's lipstick on a pig.

## The Solution

Standup eliminates human recall entirely. Instead of asking you what you did, it **pulls the data** from GitHub, Slack, and Calendar — tools Anna's runtime already integrates with natively. Then it runs **deterministic analysis** through a dedicated Python engine that classifies commits, detects blockers, and structures the output. No LLM guessing. No hallucination. The same input always produces the same honest output.

The result: a complete, accurate standup delivered in under 5 seconds from a single mention.

```
#standup

🎤 Standup — cubiczan — 2026-06-18

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

## How It Works

```
#standup
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  1. Anna activates Standup app via system_prompt_addendum │
│  2. standup-playbook Skill orchestrates the workflow      │
│     ↓                                                     │
│  3. Built-in GitHub tool  → commits, PRs, issues (24h)   │
│  4. Built-in Slack tool   → @mentions, urgent threads    │
│  5. Built-in Calendar tool → today's meetings            │
│     ↓                                                     │
│  6. standup-tool Executa (Python, JSON-RPC 2.0)           │
│     • Classifies commits into 8 categories                │
│     • Detects blockers from 12+ signal patterns           │
│     • Produces structured standup with metrics            │
│     ↓                                                     │
│  7. Agent formats output using playbook guidelines        │
│     ↓                                                     │
│  Structured standup delivered to user in <5 seconds       │
└──────────────────────────────────────────────────────────┘
```

Fully automated. Zero manual input. Zero hallucination risk — the analysis is deterministic Python, not LLM inference.

## Architecture

Standup is a native Anna App that combines all three Executa types the platform provides:

### Tool Executa: `standup-tool` (Python, zero dependencies)

A JSON-RPC 2.0 plugin over stdin/stdout. Pure Python stdlib — no pip install, no virtual environment, no container. A single 430-line file that ships instantly.

| Tool | What It Does |
|------|-------------|
| `format_standup` | Takes raw commits, PRs, issues, and messages. Classifies commits into 8 categories (feature, bugfix, refactor, testing, docs, merge, release, infra). Summarizes PR merge activity. Detects blockers from labels, comments, and message patterns. Outputs a structured standup with per-category counts and a metrics summary line. |
| `detect_blockers` | Focused blocker scanner. Examines PR comments, issue labels, Slack messages, and review statuses for 12+ blocking signals. Returns a severity-ranked (high/medium), deduplicated list with source attribution. |
| `weekly_digest` | Aggregates daily standups into a weekly team report. Computes velocity metrics, identifies top themes across the week, generates a daily breakdown table, and produces actionable recommendations based on velocity and blocker patterns. |
| `health_score` | Calculates a team health score (0-100, letter grade A-D) from four weighted dimensions: consistency (20%), blocker health (30%), activity level (30%), and velocity trend (20%). |

### Skill Executa: `standup-playbook` (SKILL.md)

A declarative methodology document — "prompt-as-code" — that governs how the Anna agent behaves regardless of which LLM model routes the request:

- **Data gathering protocol**: exactly which built-in tools to call, in what order, with what parameters
- **Tool invocation guide**: how to structure `format_standup` and `detect_blockers` calls
- **Output formatting rules**: the standup template, tone (concise, action verbs, 30-second read), special case handling (no activity, all blockers, new team members, weekends)
- **Extended formats**: weekly digest table and health report structure

Change the playbook, change the behavior — no code deploy needed.

### App Manifest

Bundles both Executas with a `system_prompt_addendum` that activates the entire workflow when the user types `#standup`. Declares `standup-tool` as a required Tool Executa and `standup-playbook` as a required Skill Executa.

```
standup-anna/
├── executa/standup-tool/
│   └── standup_tool.py       # 4 tools, 430 lines, zero deps
├── skill/standup-playbook/
│   └── SKILL.md              # 110 lines of declarative methodology
├── app/
│   └── manifest.json          # Anna App manifest v1
├── logo.png                   # 480x480
├── thumbnail.png              # 1344x768
└── README.md
```

## Blocker Detection

This is the highest-value feature. Developers consistently underreport blockers — it's human nature. Standup catches them automatically from 12+ signal patterns:

**From PRs:**
- Labels: `blocked`, `needs-review`, `waiting`, `hold`
- Comment keywords: "blocked on", "waiting on", "depends on", "can't merge", "held up", "stuck"
- Review status: `no_reviewers`, `changes_requested`

**From Issues:**
- Labels: `blocked`, `needs-review`, `waiting`, `hold`, `urgent`, `critical`

**From Slack:**
- Message keywords: "blocked", "waiting on you", "urgent", "asap", "when can you"

All signals are deduplicated, tagged with source and severity, and sorted critical-first. A developer who runs `#standup` will surface blockers they would have otherwise hidden until next week's retrospective.

## Why This Only Works on Anna

Standup is not a wrapper around ChatGPT. It's a native Anna App that leverages three platform capabilities no other runtime provides together:

**1. Pre-connected integrations.** Anna already has GitHub, Slack, and Calendar tools. Standup needs zero OAuth flows, zero API tokens, zero permission screens. The user installs the app and it works immediately — because Anna already did the hard part of connecting to their tools.

**2. Deterministic Executas.** A pure LLM cannot reliably classify commits into 8 categories, detect blockers from comment text patterns, or compute weighted health scores. The Tool Executa does all of this with deterministic Python code. The Skill Executa ensures the agent follows the methodology consistently. This is the Anna pattern — LLM for orchestration, Executas for computation.

**3. Prompt-as-code.** The SKILL.md playbook is a versionable, testable document that governs agent behavior. It's not "instructions for an LLM" — it's a methodology spec that produces consistent output regardless of which model Anna routes to. Update the playbook, change the output format. No code deploy, no prompt engineering in a dashboard.

**4. Human-in-the-loop architecture.** Anna's runtime supports human review before actions. Standup is read-only today, but the architecture extends naturally to acting on blockers — assigning reviewers, escalating stale PRs, scheduling unblock sessions — all with human approval built into the runtime.

## Impact

| Problem | Before Standup | After Standup |
|---------|---------------|---------------|
| Recall bias | "I think I worked on auth stuff" | "3 feature commits, 1 bugfix, 1 refactor — classified from git history" |
| Vagueness | "Pushed some commits" | "feat: add OAuth2 flow · fix: resolve redirect loop · refactor: extract auth middleware" |
| Blocker hiding | "Nothing blocking me" | "PR 'Add OAuth2 support' — no reviewers assigned · Issue 'Update dependencies' is blocked" |
| Time waste | 15-min synchronous meeting, 12.5 hrs/week for a 5-person team | 5-second async mention: `#standup` |

For a 5-person team, that's **12.5 hours per week reclaimed** — not from eliminating standups, but from making them actually work.

## Tech Stack

- **Protocol**: JSON-RPC 2.0 over stdio (Anna Executa specification)
- **Language**: Python 3.10+ (stdlib only — zero external dependencies)
- **Skill Format**: SKILL.md with YAML frontmatter (Anna Skill Executa specification)
- **App Format**: JSON manifest v1 (Anna App specification)
- **Total size**: 430 lines Python + 110 lines SKILL.md + 1 JSON manifest

---

**Team**: Cubiczan · **Category**: Productivity
Built with [Anna Developer Platform](https://anna.partners/developers) for the [Anna AI-Native App Hackathon](https://dorahacks.io/hackathon/2204/detail).