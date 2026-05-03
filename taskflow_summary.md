# TaskFlow — Project Summary

> A local desktop task tracker built with Python + Flask, running in the browser, storing data in CSV files.

---

## Project Idea

The goal was to build a **simple, local-first desktop app** for personal habit and task tracking — no cloud, no accounts, no heavy backend. Just run a Python script and it opens in your browser.

### Core requirements defined during planning:

- **Task management** — Add tasks grouped by type/category (e.g. Physical, Mental, Work), with optional sub-tasks, descriptions, and a daily frequency (how many times per day)
- **Daily tracker** — Multiple checkboxes per task matching the required frequency (e.g. 2×/day = 2 checkboxes). A task counts as a full success only when all checkboxes are checked
- **Reports** — Weekly and monthly views showing success rates, missed tasks, heatmaps, and bar charts

### Key design decisions:

| Decision | Choice | Reason |
|---|---|---|
| Tech stack | Python + Flask + Browser | Most interactive, fastest startup, no Electron overhead |
| Completion tracking | Multiple checkboxes per frequency | Clearest UX — each repetition is a distinct checkbox |
| Success definition | All checkboxes checked = success | Each repetition treated as a separate task |
| Data storage | Plain CSV files | Simple, portable, openable in Excel |

---

## What Was Built

### Version 1 — Single file app

Initial build as a single `index.html` template with everything in one file.

**Files:**
```
tasktracker/
├── run.py           ← launcher (auto-opens browser)
├── app.py           ← Flask backend + all API routes
├── tasks.csv        ← auto-created on first run
├── logs.csv         ← auto-created on first run
└── templates/
    └── index.html   ← entire frontend (HTML + CSS + JS)
```

**Features built:**
- Add tasks with Type, Name, Sub-task, Description, Times/Day
- Tasks auto-grouped by type in the UI
- Daily tracker with per-task checkboxes and live progress bar
- Navigate to previous days via Prev/Next buttons
- Weekly and monthly report with heatmap + bar chart per task

---

### Version 2 — Split into multiple pages + enhanced reports

Refactored into proper multi-page Flask app using Jinja2 template inheritance. `index.html` became the base layout; each page extends it.

**Files:**
```
tasktracker/
├── run.py
├── app.py
├── tasks.csv
├── logs.csv
└── templates/
    ├── index.html    ← base layout: nav, shared CSS, shared JS
    ├── manage.html   ← Manage Tasks page
    ├── tracker.html  ← Daily Tracker page
    └── report.html   ← Reports page
```

**What changed:**
- Each page is now a separate route (`/manage`, `/tracker`, `/report`)
- Active nav link highlights automatically via Jinja2 `active` variable
- Shared styles, toast notifications, and utility functions defined once in `index.html`

**New report features added:**

| Section | What it shows |
|---|---|
| **Overall** | Single % score across all tasks, perfect/partial/missed day count, best & worst task callout, full heatmap + bar chart |
| **By Category** | Per-type aggregated %, heatmap where success = *all* tasks in that type succeeded that day |
| **Task Breakdown** | Collapsible cards per category, each task showing its own heatmap and bar chart |

---

## How It Works

### Backend (`app.py`)

- **Flask** serves 4 routes: `/`, `/manage`, `/tracker`, `/report`
- **REST API** over JSON for all data operations:
  - `GET /api/tasks` — list all tasks
  - `POST /api/tasks` — add a task
  - `DELETE /api/tasks/<id>` — remove a task and its logs
  - `GET /api/logs?date=YYYY-MM-DD` — get checkboxes for a day
  - `POST /api/logs` — save a checkbox state
  - `GET /api/report?period=weekly|monthly` — get full report data

### Data (`tasks.csv` + `logs.csv`)

**tasks.csv** — one row per task:
```
id, type, name, subtask, description, frequency, parent_id
```

**logs.csv** — one row per checkbox per day:
```
date, task_id, occurrence, done
```
`occurrence` is the repetition number (1, 2, 3…) for tasks with frequency > 1.

### Frontend

- Pure HTML + CSS + JavaScript (no frameworks)
- Jinja2 template inheritance — base layout in `index.html`, pages extend with `{% block content %}`
- All data fetched from the API via `fetch()` on page load
- Live UI updates on checkbox toggle without full page reload

### Report logic

- **Success** for a task on a day = all `frequency` occurrences marked done
- **Partial** = at least one, but not all, occurrences done
- **Fail** = zero occurrences done
- **Type-level success** = all tasks in that type succeeded that day
- **Overall success** = all tasks across all types succeeded that day

---

## How to Run

```bash
# 1. Install dependency (one time)
pip install flask

# 2. Start the app
cd C:\Projects\TaskTracker
python run.py

# App opens automatically at http://localhost:5050
# Press Ctrl+C to stop
```

---

## Future Ideas

- Export report as PDF or CSV
- Streak tracking (consecutive successful days)
- Notifications / reminders
- Task archiving instead of hard delete
- Color coding per category
