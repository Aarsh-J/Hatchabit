# TaskFlow — Project Summary

> A local desktop habit and task tracker built with Python + Flask, running in the browser, storing data in CSV files. No cloud, no accounts — just run and go.

---

## Project Idea

Build a simple, local-first app for personal habit tracking. The core idea: define tasks once, then every day check them off. Reports show how consistent you've been over time.

### Core requirements

- **Task management** — Add tasks grouped by type/category (e.g. Physical, Mental, Work), with optional sub-tasks, descriptions, and a daily frequency (how many times per day)
- **Daily tracker** — Multiple checkboxes per task matching the required frequency (e.g. 2×/day = 2 checkboxes). A task counts as full success only when every checkbox is checked
- **Reports** — Weekly and monthly views with proper calendar weeks, prev/next navigation, success rates, heatmaps, and bar charts

### Key design decisions

| Decision | Choice | Reason |
|---|---|---|
| Tech stack | Python + Flask + Browser | Interactive, fast startup, no Electron overhead |
| Completion tracking | Multiple checkboxes per frequency | Each repetition is a distinct checkbox — clearest UX |
| Success definition | All checkboxes checked = success | Each repetition treated as a separate obligation |
| Data storage | Plain CSV files | Simple, portable, openable in Excel |
| Week definition | Sunday–Saturday | Standard calendar week |

---

## Current Version — v3

### Directory Structure

```
TaskFlow/
├── run.py                  ← Launcher: starts Flask and auto-opens browser
├── app.py                  ← Flask backend: all routes, API, CSV logic
├── tasks.csv               ← Auto-created on first run — task definitions
├── logs.csv                ← Auto-created on first run — daily check-in history
├── taskflow_summary.md     ← This file
├── FUTURE_WORK.md          ← Planned features with implementation notes
├── README.md               ← GitHub readme / setup guide
└── templates/
    ├── index.html          ← Base layout: shell, nav, shared CSS, shared JS
    ├── manage.html         ← Manage Tasks page
    ├── tracker.html        ← Daily Tracker page
    └── report.html         ← Reports page
```

### File Purposes

| File | Purpose |
|---|---|
| `run.py` | Entry point. Starts Flask on port 5050 and opens the browser after 0.8s |
| `app.py` | All backend logic: Flask routes, REST API, CSV read/write, report calculations, DB migration |
| `tasks.csv` | One row per task. Schema: `id, type, name, subtask, description, frequency, parent_id, created_on, is_active, removed_on` |
| `logs.csv` | One row per checkbox per day. Schema: `date, task_id, occurrence, done` |
| `templates/index.html` | Jinja2 base template. Defines the shell (topbar + sidebar + main), all CSS variables, shared utility JS (toast, esc, pctClass) |
| `templates/manage.html` | Add and delete tasks. Fetches tasks via API, groups by type, renders form |
| `templates/tracker.html` | Daily check-in view. Date navigation, checkboxes per task, live progress bar |
| `templates/report.html` | Reports view. Period toggle, week/month navigation with prev/next, all three report sections |

---

## How It Works

### Backend (`app.py`)

Flask serves 4 page routes and a REST API over JSON.

**Page routes:**
- `GET /` → `index.html` (redirects to tracker in practice)
- `GET /manage` → `manage.html`
- `GET /tracker` → `tracker.html`
- `GET /report` → `report.html`

**API routes:**

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/api/tasks` | List all tasks (including archived) |
| POST | `/api/tasks` | Add a new task |
| DELETE | `/api/tasks/<id>` | Hard delete task + all its logs |
| GET | `/api/logs?date=YYYY-MM-DD` | Get all checkbox states for a day |
| POST | `/api/logs` | Save/update one checkbox state |
| GET | `/api/report?period=weekly\|monthly&offset=N` | Full report data for a period |
| GET | `/api/report/bounds` | Min/max offsets the user can navigate to |

**Startup:** `ensure_files()` creates CSVs if missing. `migrate_tasks()` automatically adds new columns to an existing `tasks.csv` without data loss.

### Data Schema

**`tasks.csv`** — one row per task:

| Column | Type | Notes |
|---|---|---|
| `id` | int | Auto-incremented |
| `type` | string | Category label (e.g. "Physical") |
| `name` | string | Task name |
| `subtask` | string | Optional sub-task label |
| `description` | string | Optional detail/note |
| `frequency` | int | How many times per day (default 1) |
| `parent_id` | int | ID of parent task if this is a sub-task |
| `created_on` | YYYY-MM-DD | Date task was added — used for report date clamping |
| `is_active` | 0 or 1 | 1 = active in daily tracker, 0 = archived (UI coming) |
| `removed_on` | YYYY-MM-DD | Date archived, empty if still active |

**`logs.csv`** — one row per checkbox per day:

| Column | Type | Notes |
|---|---|---|
| `date` | YYYY-MM-DD | The day being logged |
| `task_id` | int | References `tasks.csv` id |
| `occurrence` | int | Which repetition (1, 2, 3… up to `frequency`) |
| `done` | 0 or 1 | Whether that checkbox was checked |

### Frontend

- Pure HTML + CSS + JavaScript — no frameworks
- Jinja2 template inheritance: `index.html` is the base, all pages use `{% extends "index.html" %}` and fill `{% block content %}` and `{% block extra_script %}`
- All data fetched from API via `fetch()` on page load
- Live checkbox updates without full page reload

### Report Logic

**Per task, per day:**
- **Success** = all `frequency` occurrences marked done
- **Partial** = at least one but not all done
- **Fail** = zero done

**Date clamping:** A task is only evaluated from its `created_on` date onward (and up to `removed_on` if archived). Pre-creation days show as faint grey cells in heatmaps and are excluded from all percentage calculations.

**Type-level success** = all tasks in that type succeeded that day (only counting tasks active on that day).

**Overall success** = all active tasks across all types succeeded that day.

**Week definition:** Sunday–Saturday. The `/api/report/bounds` endpoint calculates how far back the user can navigate by finding the earliest `created_on` or log date.

---

## Version History

### v1 — Single file app
Initial build. Everything in one `index.html`. Single Flask file. Basic task add/delete, daily tracker with checkboxes, simple weekly/monthly report.

### v2 — Multi-page + enhanced reports
Refactored into proper Jinja2 template inheritance. Split into `manage.html`, `tracker.html`, `report.html`. Added collapsible type cards in reports, per-task heatmaps, bar charts, Overall / By Category / Task Breakdown sections.

### v3 — Calendar weeks + navigation (current)
- Weeks now run Sunday–Saturday instead of rolling 7-day windows
- Prev/Next navigation to browse past weeks and months
- Navigation disabled beyond the earliest date with actual data
- `tasks.csv` schema extended: `created_on`, `is_active`, `removed_on`
- Auto-migration: existing CSVs are upgraded on startup without data loss
- Heatmaps show day-of-week labels (S M T W T F S)
- Pre-creation days render as grey cells, excluded from all calculations
- Archived tasks will appear in historical reports with an "archived" badge
- New API endpoint: `GET /api/report/bounds`
