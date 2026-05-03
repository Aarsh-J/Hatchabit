from flask import Flask, render_template, request, jsonify
import csv, os
from datetime import datetime, timedelta, date
from collections import defaultdict

app = Flask(__name__)

TASKS_FILE = "tasks.csv"
LOG_FILE   = "logs.csv"

# ── FILE HELPERS ────────────────────────────────────────────────────────────

def ensure_files():
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=["id","type","name","subtask","description","frequency","parent_id"]).writeheader()
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=["date","task_id","occurrence","done"]).writeheader()

def read_tasks():
    ensure_files()
    tasks = []
    with open(TASKS_FILE, newline="") as f:
        for row in csv.DictReader(f):
            row["frequency"] = int(row["frequency"]) if row["frequency"] else 1
            tasks.append(row)
    return tasks

def write_tasks(tasks):
    with open(TASKS_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","type","name","subtask","description","frequency","parent_id"])
        w.writeheader(); w.writerows(tasks)

def read_logs():
    ensure_files()
    with open(LOG_FILE, newline="") as f:
        return list(csv.DictReader(f))

def write_logs(logs):
    with open(LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date","task_id","occurrence","done"])
        w.writeheader(); w.writerows(logs)

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
        "parent_id":   data.get("parent_id","")
    }
    tasks.append(task)
    write_tasks(tasks)
    return jsonify(task)

@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
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

# ── API: REPORT ───────────────────────────────────────────────────────────────

def _build_task_stats(tasks, logs, date_range):
    log_index = {(l["date"], l["task_id"], l["occurrence"]): l["done"] == "1" for l in logs}
    stats = []

    for task in tasks:
        freq         = int(task["frequency"])
        daily_results = {}
        success_days = partial_days = fail_days = 0

        for d in date_range:
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
            "success_days":  success_days,
            "partial_days":  partial_days,
            "fail_days":     fail_days,
            "success_pct":   round(success_days / len(date_range) * 100) if date_range else 0,
            "daily_results": daily_results,
        })
    return stats

def _build_type_summary(stats, date_range):
    groups = defaultdict(list)
    for s in stats:
        groups[s["type"]].append(s)

    summary = {}
    for typ, items in groups.items():
        # per-day aggregate: success only if ALL tasks in type succeeded that day
        day_status = {}
        for d in date_range:
            results = [s["daily_results"].get(d, "fail") for s in items]
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
    today  = date.today()
    start  = today - timedelta(days=6 if period == "weekly" else 29)

    date_range = [(start + timedelta(days=i)).isoformat() for i in range((today - start).days + 1)]

    tasks = read_tasks()
    logs  = read_logs()

    task_stats   = _build_task_stats(tasks, logs, date_range)
    type_summary = _build_type_summary(task_stats, date_range)

    # overall per-day: success if every task succeeded
    overall_day = {}
    for d in date_range:
        results = [s["daily_results"].get(d, "fail") for s in task_stats]
        if not results:
            overall_day[d] = "fail"
        elif all(r == "success" for r in results):
            overall_day[d] = "success"
        elif all(r == "fail" for r in results):
            overall_day[d] = "fail"
        else:
            overall_day[d] = "partial"

    overall_pct = (round(sum(s["success_pct"] for s in task_stats) / len(task_stats))
                   if task_stats else 0)

    return jsonify({
        "period":       period,
        "date_range":   date_range,
        "task_stats":   task_stats,
        "type_summary": type_summary,
        "overall": {
            "pct":       overall_pct,
            "day_status": overall_day,
            "total_tasks": len(task_stats),
        }
    })

# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_files()
    import webbrowser, threading
    threading.Timer(0.8, lambda: webbrowser.open("http://localhost:5050")).start()
    app.run(port=5050, debug=False)
