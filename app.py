from flask import Flask, render_template, request, jsonify
import csv, os
from datetime import datetime, timedelta, date
from collections import defaultdict

app = Flask(__name__)

TASKS_FILE = "tasks.csv"
LOG_FILE   = "logs.csv"

TASK_FIELDS = ["id","type","name","subtask","description","frequency","parent_id","created_on","is_active","removed_on"]
LOG_FIELDS  = ["date","task_id","occurrence","done"]

# ── FILE HELPERS ────────────────────────────────────────────────────────────

def ensure_files():
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=TASK_FIELDS).writeheader()
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=LOG_FIELDS).writeheader()

def migrate_tasks():
    """Add created_on / is_active / removed_on to existing tasks.csv if missing."""
    if not os.path.exists(TASKS_FILE):
        return
    with open(TASKS_FILE, newline="") as f:
        reader = csv.DictReader(f)
        existing_fields = reader.fieldnames or []
        rows = list(reader)

    needs_migration = any(col not in existing_fields for col in ["created_on","is_active","removed_on"])
    if not needs_migration:
        return

    today = date.today().isoformat()
    for row in rows:
        row.setdefault("created_on",  today)
        row.setdefault("is_active",   "1")
        row.setdefault("removed_on",  "")

    with open(TASKS_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
        w.writeheader()
        w.writerows(rows)

def read_tasks():
    ensure_files()
    tasks = []
    with open(TASKS_FILE, newline="") as f:
        for row in csv.DictReader(f):
            row["frequency"] = int(row["frequency"]) if row["frequency"] else 1
            row.setdefault("created_on", date.today().isoformat())
            row.setdefault("is_active",  "1")
            row.setdefault("removed_on", "")
            tasks.append(row)
    return tasks

def write_tasks(tasks):
    with open(TASKS_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
        w.writeheader()
        w.writerows(tasks)

def read_logs():
    ensure_files()
    with open(LOG_FILE, newline="") as f:
        return list(csv.DictReader(f))

def write_logs(logs):
    with open(LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        w.writerows(logs)

# ── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manage")
def manage():
    return render_template("manage.html")

@app.route("/tracker")
def tracker():
    return render_template("tracker.html")

@app.route("/report")
def report():
    return render_template("report.html")

# ── API: TASKS ───────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(read_tasks())

@app.route("/api/tasks", methods=["POST"])
def add_task():
    data  = request.json
    tasks = read_tasks()
    new_id = str(max([int(t["id"]) for t in tasks], default=0) + 1)
    task = {
        "id":          new_id,
        "type":        data.get("type",""),
        "name":        data.get("name",""),
        "subtask":     data.get("subtask",""),
        "description": data.get("description",""),
        "frequency":   data.get("frequency", 1),
        "parent_id":   data.get("parent_id",""),
        "created_on":  date.today().isoformat(),
        "is_active":   "1",
        "removed_on":  "",
    }
    tasks.append(task)
    write_tasks(tasks)
    return jsonify(task)

@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    # Hard delete: remove task + all its logs permanently
    tasks = [t for t in read_tasks() if t["id"] != task_id and t["parent_id"] != task_id]
    write_tasks(tasks)
    write_logs([l for l in read_logs() if l["task_id"] != task_id])
    return jsonify({"ok": True})

# ── API: LOGS ────────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    date_str = request.args.get("date", str(date.today()))
    return jsonify([l for l in read_logs() if l["date"] == date_str])

@app.route("/api/logs", methods=["POST"])
def update_log():
    data       = request.json
    date_str   = data["date"]
    task_id    = data["task_id"]
    occurrence = str(data["occurrence"])
    done       = data["done"]

    logs = read_logs()
    for l in logs:
        if l["date"] == date_str and l["task_id"] == task_id and l["occurrence"] == occurrence:
            l["done"] = "1" if done else "0"
            write_logs(logs)
            return jsonify({"ok": True})

    logs.append({"date": date_str, "task_id": task_id, "occurrence": occurrence, "done": "1" if done else "0"})
    write_logs(logs)
    return jsonify({"ok": True})

# ── API: AVAILABLE WEEKS / MONTHS ────────────────────────────────────────────

def _earliest_date(tasks, logs):
    """Return the earliest date we have any data for (task creation or log)."""
    dates = []
    for t in tasks:
        if t.get("created_on"):
            dates.append(t["created_on"])
    for l in logs:
        if l.get("date"):
            dates.append(l["date"])
    return min(dates) if dates else date.today().isoformat()

def _week_bounds(offset=0):
    """Return (sun, sat) for the week at offset from current week. offset=0 = this week."""
    today = date.today()
    days_since_sunday = today.weekday() + 1  # weekday(): Mon=0..Sun=6 → Sun is +1 mod 7
    if today.weekday() == 6:                 # today IS Sunday
        days_since_sunday = 0
    this_sunday = today - timedelta(days=days_since_sunday)
    target_sunday = this_sunday + timedelta(weeks=offset)
    target_saturday = target_sunday + timedelta(days=6)
    return target_sunday, target_saturday

def _month_bounds(offset=0):
    """Return (first, last) day of the month at offset from current month."""
    today = date.today()
    # shift month
    month = today.month + offset
    year  = today.year
    while month < 1:
        month += 12; year -= 1
    while month > 12:
        month -= 12; year += 1
    first = date(year, month, 1)
    # last day
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last

@app.route("/api/report/bounds", methods=["GET"])
def get_report_bounds():
    """Return min/max offsets the user can navigate to, based on actual data."""
    tasks = read_tasks()
    logs  = read_logs()
    today = date.today()

    earliest_str = _earliest_date(tasks, logs)
    earliest = date.fromisoformat(earliest_str)

    # Weekly bounds
    week_sun, week_sat = _week_bounds(0)
    min_week_offset = 0
    offset = 0
    while True:
        s, _ = _week_bounds(offset)
        if s <= earliest:
            min_week_offset = offset
            break
        offset -= 1

    # Monthly bounds
    min_month_offset = 0
    offset = 0
    while True:
        f, _ = _month_bounds(offset)
        if f <= earliest:
            min_month_offset = offset
            break
        offset -= 1

    return jsonify({
        "earliest": earliest_str,
        "today": today.isoformat(),
        "min_week_offset":  min_week_offset,
        "max_week_offset":  0,   # can't go into future
        "min_month_offset": min_month_offset,
        "max_month_offset": 0,
    })

# ── API: REPORT ───────────────────────────────────────────────────────────────

def _build_task_stats(tasks, logs, date_range, all_dates_set):
    """
    Build per-task stats. Each task is only evaluated from its created_on date.
    Days before created_on are marked 'before_creation' and excluded from pct.
    """
    log_index = {(l["date"], l["task_id"], l["occurrence"]): l["done"] == "1" for l in logs}
    stats = []

    for task in tasks:
        freq = int(task["frequency"])
        created = task.get("created_on", date_range[0] if date_range else date.today().isoformat())
        removed = task.get("removed_on", "")

        active_dates = []
        for d in date_range:
            if d < created:
                continue  # task didn't exist yet
            if removed and d > removed:
                continue  # task was removed before this day
            active_dates.append(d)

        if not active_dates:
            continue

        daily_results = {}
        success_days = partial_days = fail_days = 0

        for d in active_dates:
            done_count = sum(log_index.get((d, task["id"], str(i+1)), False) for i in range(freq))
            if done_count == freq:
                success_days += 1; daily_results[d] = "success"
            elif done_count > 0:
                partial_days += 1; daily_results[d] = "partial"
            else:
                fail_days += 1;    daily_results[d] = "fail"

        stats.append({
            "id":            task["id"],
            "type":          task["type"],
            "name":          task["name"],
            "subtask":       task["subtask"],
            "description":   task["description"],
            "frequency":     freq,
            "created_on":    created,
            "is_active":     task.get("is_active","1"),
            "success_days":  success_days,
            "partial_days":  partial_days,
            "fail_days":     fail_days,
            "success_pct":   round(success_days / len(active_dates) * 100) if active_dates else 0,
            "active_days":   len(active_dates),
            "daily_results": daily_results,
        })
    return stats

def _build_type_summary(stats, date_range):
    groups = defaultdict(list)
    for s in stats:
        groups[s["type"]].append(s)

    summary = {}
    for typ, items in groups.items():
        day_status = {}
        for d in date_range:
            # only consider tasks that were active on this day
            active_items = [s for s in items if d in s["daily_results"]]
            if not active_items:
                continue
            results = [s["daily_results"][d] for s in active_items]
            if all(r == "success" for r in results):
                day_status[d] = "success"
            elif all(r == "fail" for r in results):
                day_status[d] = "fail"
            else:
                day_status[d] = "partial"

        success_d = sum(1 for v in day_status.values() if v == "success")
        partial_d = sum(1 for v in day_status.values() if v == "partial")
        fail_d    = sum(1 for v in day_status.values() if v == "fail")
        avg_pct   = round(sum(s["success_pct"] for s in items) / len(items)) if items else 0

        summary[typ] = {
            "type":         typ,
            "task_count":   len(items),
            "success_days": success_d,
            "partial_days": partial_d,
            "fail_days":    fail_d,
            "avg_pct":      avg_pct,
            "day_status":   day_status,
            "tasks":        items,
        }
    return summary

@app.route("/api/report", methods=["GET"])
def get_report():
    period = request.args.get("period", "weekly")
    offset = int(request.args.get("offset", 0))
    today  = date.today()

    if period == "weekly":
        start, end = _week_bounds(offset)
        end = min(end, today)  # don't show future days
    else:
        start, end = _month_bounds(offset)
        end = min(end, today)

    # Full date range for the period
    num_days   = (end - start).days + 1
    date_range = [(start + timedelta(days=i)).isoformat() for i in range(num_days)]
    all_dates  = set(date_range)

    tasks = read_tasks()
    logs  = read_logs()

    # Include tasks that were active at ANY point in this date range:
    # - created_on <= end of period
    # - either still active OR removed_on >= start of period (so we still show their data)
    relevant_tasks = []
    for t in tasks:
        created = t.get("created_on", today.isoformat())
        removed = t.get("removed_on", "")
        if created > end.isoformat():
            continue  # created after this period
        if removed and removed < start.isoformat():
            continue  # removed before this period started
        relevant_tasks.append(t)

    task_stats   = _build_task_stats(relevant_tasks, logs, date_range, all_dates)
    type_summary = _build_type_summary(task_stats, date_range)

    # overall per-day: success if every active task succeeded
    overall_day = {}
    for d in date_range:
        active = [s for s in task_stats if d in s["daily_results"]]
        if not active:
            continue
        results = [s["daily_results"][d] for s in active]
        if all(r == "success" for r in results):
            overall_day[d] = "success"
        elif all(r == "fail" for r in results):
            overall_day[d] = "fail"
        else:
            overall_day[d] = "partial"

    overall_pct = (round(sum(s["success_pct"] for s in task_stats) / len(task_stats))
                   if task_stats else 0)

    # Label for UI
    if period == "weekly":
        label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    else:
        label = start.strftime('%B %Y')

    return jsonify({
        "period":       period,
        "offset":       offset,
        "label":        label,
        "date_range":   date_range,
        "task_stats":   task_stats,
        "type_summary": type_summary,
        "overall": {
            "pct":        overall_pct,
            "day_status": overall_day,
            "total_tasks": len(task_stats),
        }
    })

# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_files()
    migrate_tasks()
    import webbrowser, threading
    threading.Timer(0.8, lambda: webbrowser.open("http://localhost:5050")).start()
    app.run(port=5050, debug=False)
