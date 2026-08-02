import os
from collections import defaultdict
from datetime import date, timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate

from auth import auth_bp
from models import Log, Task, User, db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(auth_bp)

# ── PAGE ROUTES ───────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return redirect(url_for("tracker"))

@app.route("/manage")
@login_required
def manage():
    return render_template("manage.html", active="manage")

@app.route("/tracker")
@login_required
def tracker():
    return render_template("tracker.html", active="tracker")

@app.route("/report")
@login_required
def report():
    return render_template("report.html", active="report")

# ── API: TASKS ───────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return jsonify([t.to_dict() for t in tasks])

@app.route("/api/tasks", methods=["POST"])
@login_required
def add_task():
    data = request.json
    task = Task(
        user_id=current_user.id,
        type=data.get("type", ""),
        name=data.get("name", ""),
        subtask=data.get("subtask", ""),
        description=data.get("description", ""),
        frequency=int(data.get("frequency", 1) or 1),
        parent_id=int(data["parent_id"]) if data.get("parent_id") else None,
        created_on=date.today(),
        is_active=True,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    # Hard delete: remove task + any child tasks + all related logs permanently
    Task.query.filter_by(user_id=current_user.id, id=task_id).delete()
    Task.query.filter_by(user_id=current_user.id, parent_id=task_id).delete()
    Log.query.filter_by(user_id=current_user.id, task_id=task_id).delete()
    db.session.commit()
    return jsonify({"ok": True})

# ── API: LOGS ────────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
@login_required
def get_logs():
    date_str = request.args.get("date", str(date.today()))
    logs = Log.query.filter_by(user_id=current_user.id, date=date.fromisoformat(date_str)).all()
    return jsonify([l.to_dict() for l in logs])

@app.route("/api/logs", methods=["POST"])
@login_required
def update_log():
    data = request.json
    log_date = date.fromisoformat(data["date"])
    task_id = int(data["task_id"])
    occurrence = int(data["occurrence"])
    done = bool(data["done"])

    log = Log.query.filter_by(
        user_id=current_user.id, date=log_date, task_id=task_id, occurrence=occurrence
    ).first()

    if log:
        log.done = done
    else:
        log = Log(user_id=current_user.id, date=log_date, task_id=task_id, occurrence=occurrence, done=done)
        db.session.add(log)

    db.session.commit()
    return jsonify({"ok": True})

# ── API: AVAILABLE WEEKS / MONTHS ────────────────────────────────────────────

def _earliest_date(tasks, logs):
    """Return the earliest date we have any data for (task creation or log)."""
    dates = [t.created_on for t in tasks if t.created_on]
    dates += [l.date for l in logs if l.date]
    return min(dates) if dates else date.today()

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
    month = today.month + offset
    year = today.year
    while month < 1:
        month += 12; year -= 1
    while month > 12:
        month -= 12; year += 1
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last

@app.route("/api/report/bounds", methods=["GET"])
@login_required
def get_report_bounds():
    """Return min/max offsets the user can navigate to, based on actual data."""
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    logs = Log.query.filter_by(user_id=current_user.id).all()
    today = date.today()

    earliest = _earliest_date(tasks, logs)

    min_week_offset = 0
    offset = 0
    while True:
        s, _ = _week_bounds(offset)
        if s <= earliest:
            min_week_offset = offset
            break
        offset -= 1

    min_month_offset = 0
    offset = 0
    while True:
        f, _ = _month_bounds(offset)
        if f <= earliest:
            min_month_offset = offset
            break
        offset -= 1

    return jsonify({
        "earliest": earliest.isoformat(),
        "today": today.isoformat(),
        "min_week_offset": min_week_offset,
        "max_week_offset": 0,
        "min_month_offset": min_month_offset,
        "max_month_offset": 0,
    })

# ── API: REPORT ───────────────────────────────────────────────────────────────

def _build_task_stats(tasks, logs, date_range):
    """
    Build per-task stats. Each task is only evaluated from its created_on date.
    Days before created_on are excluded from pct.
    """
    log_index = {(l.date.isoformat(), l.task_id, l.occurrence): l.done for l in logs}
    stats = []

    for task in tasks:
        freq = task.frequency or 1
        created = task.created_on.isoformat() if task.created_on else date_range[0]
        removed = task.removed_on.isoformat() if task.removed_on else ""

        active_dates = []
        for d in date_range:
            if d < created:
                continue
            if removed and d > removed:
                continue
            active_dates.append(d)

        if not active_dates:
            continue

        daily_results = {}
        success_days = partial_days = fail_days = 0

        for d in active_dates:
            done_count = sum(log_index.get((d, task.id, i + 1), False) for i in range(freq))
            if done_count == freq:
                success_days += 1; daily_results[d] = "success"
            elif done_count > 0:
                partial_days += 1; daily_results[d] = "partial"
            else:
                fail_days += 1; daily_results[d] = "fail"

        stats.append({
            "id": str(task.id),
            "type": task.type,
            "name": task.name,
            "subtask": task.subtask,
            "description": task.description,
            "frequency": freq,
            "created_on": created,
            "is_active": "1" if task.is_active else "0",
            "success_days": success_days,
            "partial_days": partial_days,
            "fail_days": fail_days,
            "success_pct": round(success_days / len(active_dates) * 100) if active_dates else 0,
            "active_days": len(active_dates),
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
        fail_d = sum(1 for v in day_status.values() if v == "fail")
        avg_pct = round(sum(s["success_pct"] for s in items) / len(items)) if items else 0

        summary[typ] = {
            "type": typ,
            "task_count": len(items),
            "success_days": success_d,
            "partial_days": partial_d,
            "fail_days": fail_d,
            "avg_pct": avg_pct,
            "day_status": day_status,
            "tasks": items,
        }
    return summary

@app.route("/api/report", methods=["GET"])
@login_required
def get_report():
    period = request.args.get("period", "weekly")
    offset = int(request.args.get("offset", 0))
    today = date.today()

    if period == "weekly":
        start, end = _week_bounds(offset)
        end = min(end, today)
    else:
        start, end = _month_bounds(offset)
        end = min(end, today)

    num_days = (end - start).days + 1
    date_range = [(start + timedelta(days=i)).isoformat() for i in range(num_days)]

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    logs = Log.query.filter_by(user_id=current_user.id).all()

    # Include tasks that were active at ANY point in this date range:
    # - created_on <= end of period
    # - either still active OR removed_on >= start of period (so we still show their data)
    relevant_tasks = []
    for t in tasks:
        created = t.created_on.isoformat() if t.created_on else today.isoformat()
        removed = t.removed_on.isoformat() if t.removed_on else ""
        if created > end.isoformat():
            continue
        if removed and removed < start.isoformat():
            continue
        relevant_tasks.append(t)

    task_stats = _build_task_stats(relevant_tasks, logs, date_range)
    type_summary = _build_type_summary(task_stats, date_range)

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

    if period == "weekly":
        label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    else:
        label = start.strftime('%B %Y')

    return jsonify({
        "period": period,
        "offset": offset,
        "label": label,
        "date_range": date_range,
        "task_stats": task_stats,
        "type_summary": type_summary,
        "overall": {
            "pct": overall_pct,
            "day_status": overall_day,
            "total_tasks": len(task_stats),
        }
    })

# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(port=5050, debug=False)
