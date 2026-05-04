# TaskFlow — Future Work

A running list of planned features and ideas, with enough detail to pick up and implement later.

---

## 1. Task Lifecycle — Archive & Hard Delete

Currently tasks only have a hard delete (removes task + all its logs permanently). The DB fields for soft-archiving (`is_active`, `removed_on`) are already added in v3 but the UI is not built yet.

### 1a. Remove from Daily Routine (Soft Archive)
- User can mark a task as "removed" — it stops showing in the Daily Tracker and Manage Tasks page
- The task's historical logs are **kept**, so reports still show its data for periods when it was active
- The task appears in reports with an "archived" badge to make clear it's no longer active
- Implementation needed:
  - Button in Manage Tasks: "Remove from routine" → sets `is_active=0` and `removed_on=today` in `tasks.csv`
  - Daily Tracker filters to only `is_active=1` tasks
  - Manage Tasks page shows archived tasks in a collapsed "Archived" section (view-only, with option to restore)
  - `GET /api/tasks` should accept a `?active_only=true` param so tracker uses it but manage page can show all

### 1b. Hard Delete (Permanent)
- User can permanently delete a task and all its historical data
- No record in `tasks.csv`, no records in `logs.csv`
- Should be behind a confirmation dialog: "This will permanently delete all history for this task. This cannot be undone."
- Already partially implemented — current `DELETE /api/tasks/<id>` does this, but it runs immediately without confirmation

---

## 2. Streak Tracking

Show consecutive successful days per task and overall.

- **Definition:** A streak is a run of consecutive calendar days where a task was fully completed (all occurrences done). Days before `created_on` don't break a streak.
- **Display ideas:**
  - In Task Breakdown cards: "🔥 Current streak: 5 days · Best streak: 12 days"
  - In Overall section: combined streak where every task succeeded
  - In Daily Tracker: small streak counter next to each task name
- **Edge cases to handle:**
  - Today not yet logged — don't break the streak, just show yesterday's streak as "active"
  - Partial days should NOT count toward streak (only full success)
  - Task was archived mid-streak — streak ends at `removed_on`

---

## 3. Export Report

Let the user download their report data.

### 3a. Export as CSV
- Flat table: `date, task_type, task_name, occurrences_required, occurrences_done, status (success/partial/fail)`
- One row per task per day for the selected period
- Button in the Reports page header: "Export CSV"
- Backend: new route `GET /api/report/export?period=weekly&offset=0` returns CSV file as download

### 3b. Export as PDF
- Render the current report view (heatmaps + charts + stats) to PDF
- Simplest approach: use browser's `window.print()` with a print stylesheet that hides nav/controls
- Better approach: generate a clean PDF server-side using `weasyprint` or `reportlab`

---

## 4. Color Coding per Category

Each task type gets a consistent color used across the UI.

- Assign colors either automatically (cycle through a palette) or let user pick in Manage Tasks
- Store `color` field in `tasks.csv` at the type level (or a separate `types.csv`)
- Use color in:
  - Type badges in Manage Tasks and Daily Tracker
  - Section headers in Reports
  - Heatmap border or tint per category in By Category section
- Palette suggestion: keep colors muted/dark-mode friendly — no bright primaries

---

## 5. Notifications / Reminders

Remind the user to log their tasks.

- Since this is a local app with no background process, true push notifications aren't straightforward
- Options:
  - **Simple:** On app open, if today has incomplete tasks, show a prominent banner "You have X tasks not yet logged today"
  - **System tray approach:** A lightweight background script (using `plyer` or `win10toast`) that fires a desktop notification at a user-set time
  - **Browser notification:** Use the Web Notifications API — ask permission on first load, then send a reminder at a configured time using `setTimeout` based on current time
- Store reminder time in a `settings.csv` or `settings.json` file

---

## 6. Settings Page

A dedicated page for app-wide preferences.

- Potential settings:
  - Reminder time (for notifications)
  - Default period on Reports page (weekly vs monthly)
  - First day of week (currently hardcoded to Sunday)
  - Theme toggle (dark only right now)
- Stored in `settings.json` in the project root
- New route `/settings` and `settings.html` template

---

## 7. Sub-task Hierarchy in Reports

Currently `parent_id` exists in the schema but sub-tasks are treated as flat tasks in reports.

- Group sub-tasks visually under their parent task in the Task Breakdown section
- Parent task row shows aggregated % across all its sub-tasks
- Sub-tasks shown as indented rows beneath the parent
- Success definition options: parent succeeds if ANY sub-task succeeds, or if ALL do (make configurable)

---

## 8. Data Backup / Restore

Simple way to back up and restore the CSV files.

- Button in a Settings or About page: "Export backup" → downloads a `.zip` of `tasks.csv` + `logs.csv`
- "Restore from backup" → file upload that replaces the CSVs (with confirmation)
- Could also add auto-backup: on each app start, copy CSVs to a `backups/` folder with a datestamp, keep last N backups

---

## 9. Quick-add from Daily Tracker

Currently adding tasks requires going to the Manage Tasks page.

- Small "+ Add task" inline in the tracker grouped by type
- Opens a minimal modal (just Type, Name, Times/Day — skip description/subtask for speed)
- Task appears immediately in today's tracker without page reload

---

## Notes

- Items marked with existing DB support: **#1 (is_active, removed_on already in schema)**
- Priority order (rough): 1a → 1b → 2 → 3a → 4 → rest
- All features should stay local-first — no external services, no accounts
