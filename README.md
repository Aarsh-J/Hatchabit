# TaskFlow

A minimal local desktop app for tracking daily habits and tasks. Runs in your browser, stores everything in plain CSV files on your machine.

**No cloud. No accounts. No background services.** Just run one Python script and it opens in your browser.

---

## What it does

**Manage Tasks** — Define tasks by category (Physical, Mental, Work, etc.), set how many times a day each must be done, and optionally add sub-tasks and descriptions.

**Daily Tracker** — Every day, check off each task as you do it. Tasks with a frequency of 2×/day show two checkboxes. A live progress bar shows how your day is going.

**Reports** — See your consistency over any past week or month. Navigate back in time with Prev/Next. Three views: overall score, per-category breakdown, and per-task heatmaps + bar charts.

---

## Setup

**Requirements:** Python 3.8+

```bash
# 1. Clone or download the project
git clone https://github.com/yourusername/taskflow.git
cd taskflow

# 2. Install the one dependency
pip install flask

# 3. Run
python run.py
```

The app opens automatically at `http://localhost:5050`. Press `Ctrl+C` in the terminal to stop it.

The two data files (`tasks.csv` and `logs.csv`) are created automatically on first run in the same folder.

---

## How to use

### Manage Tasks
- Go to **Manage Tasks** in the sidebar
- Fill in: Type, Task Name, and Times/Day (minimum fields)
- Optionally add a Sub-task label and Description
- Tasks are grouped by Type automatically
- Delete removes the task and all its history permanently

### Daily Tracker
- Go to **Daily Tracker** — it defaults to today
- Use ← Prev / Next → to navigate to other days
- Check off each box as you complete each repetition
- A task is fully done when all its boxes are checked (green = done, yellow = partial)

### Reports
- Go to **Reports**
- Toggle between **Weekly** (Sun–Sat) and **Monthly**
- Use ← Prev / Next → to browse past periods
- Navigation is disabled for periods before your first task was created
- Three sections:
  - **Overall** — single % score, perfect/partial/missed day counts, best and worst task
  - **By Category** — per-type % and heatmap
  - **Task Breakdown** — collapsible cards with per-task heatmap and bar chart

---

## Data files

Both files are plain CSV — open them in Excel or Google Sheets anytime.

**`tasks.csv`** — your task definitions:
```
id, type, name, subtask, description, frequency, parent_id, created_on, is_active, removed_on
```

**`logs.csv`** — your daily check-in history:
```
date, task_id, occurrence, done
```

`occurrence` is the repetition number (1, 2, 3…) for tasks with frequency > 1.

---

## Project structure

```
TaskFlow/
├── run.py              ← Start here
├── app.py              ← Flask backend + all API routes
├── tasks.csv           ← Auto-created — task definitions
├── logs.csv            ← Auto-created — daily history
└── templates/
    ├── index.html      ← Base layout (nav, shared styles + JS)
    ├── manage.html     ← Manage Tasks page
    ├── tracker.html    ← Daily Tracker page
    └── report.html     ← Reports page
```

---

## Tech stack

- **Python + Flask** — backend and API
- **Jinja2** — templating
- **Vanilla HTML / CSS / JS** — frontend, no frameworks
- **CSV files** — data storage

---

## Migrating from an older version

If you have an existing `tasks.csv` from a previous version, the app will automatically add any missing columns (`created_on`, `is_active`, `removed_on`) on startup. No manual steps needed, your existing data is preserved.
