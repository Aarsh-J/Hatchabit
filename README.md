# TaskFlow — Daily Progress Tracker

A minimal local desktop app to track your daily habits and tasks. Runs in your browser, stores everything in CSV files on your machine. No cloud, no accounts.

## Setup

1. Make sure you have **Python 3.8+** installed
2. Install Flask once:
   ```
   pip install flask
   ```
3. Run the app:
   ```
   python run.py
   ```
   It will open automatically at `http://localhost:5050`

## How to use

### Manage Tasks
- Set a **Type** (e.g. Physical, Mental, Work)
- Add a **Task Name** and optional **Sub-task**
- Add a **Description** (e.g. "Run 20 mins")
- Set **Times/Day** — how many times per day you must do it (e.g. 2 = two checkboxes in tracker)

### Daily Tracker
- Navigate by date using Prev/Next
- Each task shows one checkbox per required repetition
- Progress bar fills as you check them off
- Green = fully done, Yellow = partial

### Reports
- Toggle between **Weekly** (7 days) and **Monthly** (30 days)
- Heatmap shows day-by-day: green=success, yellow=partial, red=missed
- Bar chart shows your consistency over time
- Stats show your overall %, best task, and task needing most work

## Data Files
- `tasks.csv` — your task definitions
- `logs.csv` — your daily check-in history

Both are plain CSV files you can open in Excel or Google Sheets.
