import os
from collections import defaultdict
from datetime import date, timedelta

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate

from auth import auth_bp
from models import Habit, Log, Subtask, Task, ToDo, User, db, HABIT_PALETTE

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

@app.route("/todo")
@login_required
def todo():
    return render_template("todo.html", active="todo")

# ── HELPERS ──────────────────────────────────────────────────────────────────

def _get_owned_task(task_id):
    task = Task.query.filter_by(user_id=current_user.id, id=task_id).first()
    if not task:
        abort(404)
    return task

def _get_owned_subtask(subtask_id):
    st = (
        Subtask.query.join(Task, Subtask.task_id == Task.id)
        .filter(Subtask.id == subtask_id, Task.user_id == current_user.id)
        .first()
    )
    if not st:
        abort(404)
    return st

def _valid_unit(unit):
    return unit if unit in ("day", "week", "month") else "day"

def _period_bounds(d, unit):
    """Return (start, end) date bounds of the week/month containing date d."""
    if unit == "week":
        days_since_sunday = (d.weekday() + 1) % 7
        start = d - timedelta(days=days_since_sunday)
        end = start + timedelta(days=6)
    else:
        start = date(d.year, d.month, 1)
        if d.month == 12:
            end = date(d.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(d.year, d.month + 1, 1) - timedelta(days=1)
    return start, end

# ── API: HABITS ──────────────────────────────────────────────────────────────

@app.route("/api/habits", methods=["GET"])
@login_required
def get_habits():
    q = Habit.query.filter_by(user_id=current_user.id)
    if request.args.get("active_only") == "true":
        q = q.filter_by(is_active=True)
    return jsonify([h.to_dict() for h in q.order_by(Habit.created_on).all()])

@app.route("/api/habits", methods=["POST"])
@login_required
def add_habit():
    data = request.json
    existing_count = Habit.query.filter_by(user_id=current_user.id).count()
    habit = Habit(
        user_id=current_user.id,
        name=data.get("name", ""),
        description=data.get("description", ""),
        color=HABIT_PALETTE[existing_count % len(HABIT_PALETTE)],
        created_on=date.today(),
        is_active=True,
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify(habit.to_dict())

@app.route("/api/habits/<int:habit_id>", methods=["PUT"])
@login_required
def update_habit(habit_id):
    habit = Habit.query.filter_by(user_id=current_user.id, id=habit_id).first()
    if not habit:
        abort(404)
    data = request.json
    if "name" in data: habit.name = data["name"]
    if "description" in data: habit.description = data["description"]
    if "color" in data: habit.color = data["color"]
    db.session.commit()
    return jsonify(habit.to_dict())

@app.route("/api/habits/<int:habit_id>", methods=["DELETE"])
@login_required
def delete_habit(habit_id):
    task_ids = [t.id for t in Task.query.filter_by(user_id=current_user.id, habit_id=habit_id).all()]
    if task_ids:
        subtask_ids = [s.id for s in Subtask.query.filter(Subtask.task_id.in_(task_ids)).all()]
        if subtask_ids:
            Log.query.filter(Log.user_id == current_user.id, Log.subtask_id.in_(subtask_ids)).delete(synchronize_session=False)
            Subtask.query.filter(Subtask.id.in_(subtask_ids)).delete(synchronize_session=False)
        Log.query.filter(Log.user_id == current_user.id, Log.task_id.in_(task_ids)).delete(synchronize_session=False)
        Task.query.filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    Habit.query.filter_by(user_id=current_user.id, id=habit_id).delete()
    db.session.commit()
    return jsonify({"ok": True})

# ── API: TASKS ───────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    active_only = request.args.get("active_only") == "true"

    q = Task.query.filter_by(user_id=current_user.id)
    if active_only:
        q = q.filter_by(is_active=True)
    tasks = q.order_by(Task.created_on).all()

    task_ids = [t.id for t in tasks]
    subtasks = Subtask.query.filter(Subtask.task_id.in_(task_ids)).all() if task_ids else []
    if active_only:
        subtasks = [s for s in subtasks if s.is_active]

    subtasks_by_task = defaultdict(list)
    for s in subtasks:
        subtasks_by_task[s.task_id].append(s)

    result = []
    for t in tasks:
        d = t.to_dict()
        d["subtasks"] = [s.to_dict() for s in subtasks_by_task.get(t.id, [])]
        result.append(d)
    return jsonify(result)

@app.route("/api/tasks", methods=["POST"])
@login_required
def add_task():
    data = request.json
    task = Task(
        user_id=current_user.id,
        habit_id=int(data["habit_id"]),
        name=data.get("name", ""),
        description=data.get("description", ""),
        frequency=int(data.get("frequency", 1) or 1),
        unit=_valid_unit(data.get("unit")),
        created_on=date.today(),
        is_active=True,
    )
    db.session.add(task)
    db.session.commit()
    d = task.to_dict()
    d["subtasks"] = []
    return jsonify(d)

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    task = _get_owned_task(task_id)
    data = request.json
    if "habit_id" in data: task.habit_id = int(data["habit_id"])
    if "name" in data: task.name = data["name"]
    if "description" in data: task.description = data["description"]
    if "frequency" in data: task.frequency = int(data["frequency"] or 1)
    if "unit" in data: task.unit = _valid_unit(data["unit"])
    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/api/tasks/<int:task_id>/archive", methods=["POST"])
@login_required
def archive_task(task_id):
    task = _get_owned_task(task_id)
    task.is_active = False
    task.removed_on = date.today()
    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/api/tasks/<int:task_id>/restore", methods=["POST"])
@login_required
def restore_task(task_id):
    task = _get_owned_task(task_id)
    task.is_active = True
    task.removed_on = None
    db.session.commit()
    return jsonify(task.to_dict())

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    # Hard delete: remove task + subtasks + all related logs permanently
    subtask_ids = [s.id for s in Subtask.query.filter_by(task_id=task_id).all()]
    if subtask_ids:
        Log.query.filter(Log.user_id == current_user.id, Log.subtask_id.in_(subtask_ids)).delete(synchronize_session=False)
        Subtask.query.filter(Subtask.id.in_(subtask_ids)).delete(synchronize_session=False)
    Log.query.filter_by(user_id=current_user.id, task_id=task_id).delete()
    Task.query.filter_by(user_id=current_user.id, id=task_id).delete()
    db.session.commit()
    return jsonify({"ok": True})

# ── API: SUBTASKS ────────────────────────────────────────────────────────────

@app.route("/api/tasks/<int:task_id>/subtasks", methods=["POST"])
@login_required
def add_subtask(task_id):
    _get_owned_task(task_id)  # ensures ownership
    data = request.json
    st = Subtask(
        task_id=task_id,
        name=data.get("name", ""),
        description=data.get("description", ""),
        frequency=int(data.get("frequency", 1) or 1),
        unit=_valid_unit(data.get("unit")),
        created_on=date.today(),
        is_active=True,
    )
    db.session.add(st)
    db.session.commit()
    return jsonify(st.to_dict())

@app.route("/api/subtasks/<int:subtask_id>", methods=["PUT"])
@login_required
def update_subtask(subtask_id):
    st = _get_owned_subtask(subtask_id)
    data = request.json
    if "name" in data: st.name = data["name"]
    if "description" in data: st.description = data["description"]
    if "frequency" in data: st.frequency = int(data["frequency"] or 1)
    if "unit" in data: st.unit = _valid_unit(data["unit"])
    db.session.commit()
    return jsonify(st.to_dict())

@app.route("/api/subtasks/<int:subtask_id>/archive", methods=["POST"])
@login_required
def archive_subtask(subtask_id):
    st = _get_owned_subtask(subtask_id)
    st.is_active = False
    st.removed_on = date.today()
    db.session.commit()
    return jsonify(st.to_dict())

@app.route("/api/subtasks/<int:subtask_id>/restore", methods=["POST"])
@login_required
def restore_subtask(subtask_id):
    st = _get_owned_subtask(subtask_id)
    st.is_active = True
    st.removed_on = None
    db.session.commit()
    return jsonify(st.to_dict())

@app.route("/api/subtasks/<int:subtask_id>", methods=["DELETE"])
@login_required
def delete_subtask(subtask_id):
    st = _get_owned_subtask(subtask_id)
    Log.query.filter_by(user_id=current_user.id, subtask_id=subtask_id).delete()
    db.session.delete(st)
    db.session.commit()
    return jsonify({"ok": True})

# ── API: TODOS ───────────────────────────────────────────────────────────────

def _get_owned_todo(todo_id):
    todo = ToDo.query.filter_by(user_id=current_user.id, id=todo_id).first()
    if not todo:
        abort(404)
    return todo

@app.route("/api/todos", methods=["GET"])
@login_required
def get_todos():
    q = ToDo.query.filter_by(user_id=current_user.id)
    todos = q.order_by(ToDo.is_done, ToDo.deadline.is_(None), ToDo.deadline, ToDo.created_on).all()
    return jsonify([t.to_dict() for t in todos])

@app.route("/api/todos", methods=["POST"])
@login_required
def add_todo():
    data = request.json
    deadline = date.fromisoformat(data["deadline"]) if data.get("deadline") else None
    todo = ToDo(
        user_id=current_user.id,
        name=data.get("name", ""),
        description=data.get("description", ""),
        deadline=deadline,
        created_on=date.today(),
        is_done=False,
    )
    db.session.add(todo)
    db.session.commit()
    return jsonify(todo.to_dict())

@app.route("/api/todos/<int:todo_id>", methods=["PUT"])
@login_required
def update_todo(todo_id):
    todo = _get_owned_todo(todo_id)
    data = request.json
    if "name" in data: todo.name = data["name"]
    if "description" in data: todo.description = data["description"]
    if "deadline" in data: todo.deadline = date.fromisoformat(data["deadline"]) if data["deadline"] else None
    db.session.commit()
    return jsonify(todo.to_dict())

@app.route("/api/todos/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    todo = _get_owned_todo(todo_id)
    todo.is_done = not todo.is_done
    todo.completed_on = date.today() if todo.is_done else None
    db.session.commit()
    return jsonify(todo.to_dict())

@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
@login_required
def delete_todo(todo_id):
    _get_owned_todo(todo_id)
    ToDo.query.filter_by(user_id=current_user.id, id=todo_id).delete()
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
    task_id = int(data["task_id"]) if data.get("task_id") else None
    subtask_id = int(data["subtask_id"]) if data.get("subtask_id") else None
    occurrence = int(data["occurrence"])
    done = bool(data["done"])

    q = Log.query.filter_by(
        user_id=current_user.id, date=log_date, task_id=task_id, subtask_id=subtask_id, occurrence=occurrence
    )
    log = q.first()

    if log:
        log.done = done
    else:
        log = Log(
            user_id=current_user.id, date=log_date, task_id=task_id, subtask_id=subtask_id,
            occurrence=occurrence, done=done,
        )
        db.session.add(log)

    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/logs/period-progress", methods=["GET"])
@login_required
def get_period_progress():
    """For week/month-unit tasks & subtasks, how many occurrences are logged
    done within the period (week/month) containing the given date."""
    date_str = request.args.get("date", str(date.today()))
    d = date.fromisoformat(date_str)

    tasks = Task.query.filter_by(user_id=current_user.id, is_active=True).all()
    task_ids = [t.id for t in tasks]
    subtasks = (
        Subtask.query.filter(Subtask.task_id.in_(task_ids), Subtask.is_active == True).all()
        if task_ids else []
    )

    result = {"tasks": {}, "subtasks": {}}

    def compute(entity, is_subtask):
        unit = entity.unit or "day"
        if unit == "day":
            return
        start, end = _period_bounds(d, unit)
        q = Log.query.filter(
            Log.user_id == current_user.id,
            Log.date >= start, Log.date <= end,
            Log.occurrence == 1, Log.done == True,
        )
        q = q.filter(Log.subtask_id == entity.id) if is_subtask else q.filter(Log.task_id == entity.id)
        done = q.count()
        bucket = result["subtasks"] if is_subtask else result["tasks"]
        bucket[str(entity.id)] = {
            "done": done, "freq": entity.frequency or 1, "unit": unit,
            "period_start": start.isoformat(), "period_end": end.isoformat(),
        }

    for t in tasks:
        compute(t, False)
    for s in subtasks:
        compute(s, True)

    return jsonify(result)

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

# ── STREAKS / STATS HELPERS ─────────────────────────────────────────────────

def _compute_streak(active_dates, daily_results):
    """
    current/best consecutive-success-day counts.
    Partial days don't count as success. Today isn't counted as a break if it
    isn't yet a success (it may just not be logged yet).
    """
    today_str = date.today().isoformat()
    seq = []
    for d in sorted(active_dates):
        status = daily_results.get(d)
        if status is None:
            continue
        if d == today_str and status != "success":
            continue
        seq.append(status == "success")

    best = running = 0
    for ok in seq:
        if ok:
            running += 1
            best = max(best, running)
        else:
            running = 0
    return {"current": running, "best": best}

def _aggregate_day_status(daily_results_list, date_range):
    """Combine several entities' daily_results dicts into one day_status dict:
    success only if ALL active entities succeeded that day, fail only if ALL failed."""
    day_status = {}
    for d in date_range:
        active = [dr[d] for dr in daily_results_list if d in dr]
        if not active:
            continue
        if all(r == "success" for r in active):
            day_status[d] = "success"
        elif all(r == "fail" for r in active):
            day_status[d] = "fail"
        else:
            day_status[d] = "partial"
    return day_status

def _stats_for_entity(entity, freq, log_index, is_subtask, date_range, unit="day"):
    created = entity.created_on.isoformat() if entity.created_on else date_range[0]
    removed = entity.removed_on.isoformat() if entity.removed_on else ""

    active_dates = []
    for d in date_range:
        if d < created:
            continue
        if removed and d > removed:
            continue
        active_dates.append(d)

    if not active_dates:
        return None

    daily_results = {}
    success_days = partial_days = fail_days = 0

    if unit == "day":
        for d in active_dates:
            done_count = sum(1 for i in range(freq) if log_index.get((d, entity.id, i + 1, is_subtask), False))
            if done_count == freq:
                success_days += 1; daily_results[d] = "success"
            elif done_count > 0:
                partial_days += 1; daily_results[d] = "partial"
            else:
                fail_days += 1; daily_results[d] = "fail"
        result_dates = active_dates
    else:
        # Group active dates into weeks/months; each period gets ONE representative
        # entry (the latest active day within it) so streaks/reports judge success
        # per-period rather than per-day. An in-progress period's rep day is the
        # most recent active day so far, which lets _compute_streak's "today isn't
        # a break yet" rule apply naturally at the period level too.
        periods = defaultdict(list)
        for d in active_dates:
            start, _ = _period_bounds(date.fromisoformat(d), unit)
            periods[start].append(d)

        result_dates = []
        for start in sorted(periods.keys()):
            days_in_period = periods[start]
            rep_day = max(days_in_period)
            done_count = sum(1 for d in days_in_period if log_index.get((d, entity.id, 1, is_subtask), False))
            if done_count >= freq:
                success_days += 1; daily_results[rep_day] = "success"
            elif done_count > 0:
                partial_days += 1; daily_results[rep_day] = "partial"
            else:
                fail_days += 1; daily_results[rep_day] = "fail"
            result_dates.append(rep_day)

    return {
        "active_dates": result_dates,
        "daily_results": daily_results,
        "success_days": success_days,
        "partial_days": partial_days,
        "fail_days": fail_days,
        "success_pct": round(success_days / len(result_dates) * 100) if result_dates else 0,
        "active_days": len(result_dates),
    }

def _build_task_stats(tasks, subtasks_by_task, logs, date_range):
    """
    Build per-task (and nested per-subtask) stats. A task with subtasks derives
    its own daily result from ALL its subtasks succeeding that day; a task with
    no subtasks is judged on its own frequency, same as before.
    """
    log_index = {}
    for l in logs:
        d = l.date.isoformat()
        if l.subtask_id:
            log_index[(d, l.subtask_id, l.occurrence, True)] = l.done
        elif l.task_id:
            log_index[(d, l.task_id, l.occurrence, False)] = l.done

    stats = []
    for task in tasks:
        subtask_stats = []
        for st in subtasks_by_task.get(task.id, []):
            s = _stats_for_entity(st, st.frequency or 1, log_index, True, date_range, st.unit or "day")
            if not s:
                continue
            subtask_stats.append({
                "id": str(st.id),
                "task_id": str(task.id),
                "name": st.name,
                "description": st.description,
                "frequency": st.frequency or 1,
                "unit": st.unit or "day",
                "created_on": st.created_on.isoformat() if st.created_on else "",
                "is_active": "1" if st.is_active else "0",
                **s,
                "streak": _compute_streak(s["active_dates"], s["daily_results"]),
            })

        if subtask_stats:
            merged = _aggregate_day_status([ss["daily_results"] for ss in subtask_stats], date_range)
            active_dates = sorted(merged.keys())
            success_days = sum(1 for v in merged.values() if v == "success")
            partial_days = sum(1 for v in merged.values() if v == "partial")
            fail_days = sum(1 for v in merged.values() if v == "fail")
            entity_stat = {
                "active_dates": active_dates,
                "daily_results": merged,
                "success_days": success_days,
                "partial_days": partial_days,
                "fail_days": fail_days,
                "success_pct": round(success_days / len(active_dates) * 100) if active_dates else 0,
                "active_days": len(active_dates),
            }
        else:
            entity_stat = _stats_for_entity(task, task.frequency or 1, log_index, False, date_range, task.unit or "day")

        if not entity_stat:
            continue

        stats.append({
            "id": str(task.id),
            "habit_id": str(task.habit_id),
            "name": task.name,
            "description": task.description,
            "frequency": task.frequency or 1,
            "unit": task.unit or "day",
            "created_on": task.created_on.isoformat() if task.created_on else "",
            "is_active": "1" if task.is_active else "0",
            "subtasks": subtask_stats,
            **entity_stat,
            "streak": _compute_streak(entity_stat["active_dates"], entity_stat["daily_results"]),
        })
    return stats

def _build_habit_summary(stats, habits_by_id, date_range):
    groups = defaultdict(list)
    for s in stats:
        groups[s["habit_id"]].append(s)

    summary = {}
    for habit_id, items in groups.items():
        habit = habits_by_id.get(int(habit_id))
        day_status = _aggregate_day_status([it["daily_results"] for it in items], date_range)
        active_dates = sorted(day_status.keys())

        success_d = sum(1 for v in day_status.values() if v == "success")
        partial_d = sum(1 for v in day_status.values() if v == "partial")
        fail_d = sum(1 for v in day_status.values() if v == "fail")
        avg_pct = round(sum(s["success_pct"] for s in items) / len(items)) if items else 0

        summary[habit_id] = {
            "habit_id": habit_id,
            "name": habit.name if habit else "Unknown",
            "description": habit.description if habit else "",
            "color": habit.color if habit else "#e8ff6b",
            "task_count": len(items),
            "success_days": success_d,
            "partial_days": partial_d,
            "fail_days": fail_d,
            "avg_pct": avg_pct,
            "day_status": day_status,
            "tasks": items,
            "streak": _compute_streak(active_dates, day_status),
        }
    return summary

@app.route("/api/streaks", methods=["GET"])
@login_required
def get_streaks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    task_ids = [t.id for t in tasks]
    subtasks = Subtask.query.filter(Subtask.task_id.in_(task_ids)).all() if task_ids else []
    logs = Log.query.filter_by(user_id=current_user.id).all()

    today = date.today()
    dates = [t.created_on for t in tasks if t.created_on] + [s.created_on for s in subtasks if s.created_on]
    dates += [l.date for l in logs if l.date]
    earliest = min(dates) if dates else today
    date_range = [(earliest + timedelta(days=i)).isoformat() for i in range((today - earliest).days + 1)]

    subtasks_by_task = defaultdict(list)
    for s in subtasks:
        subtasks_by_task[s.task_id].append(s)

    task_stats = _build_task_stats(tasks, subtasks_by_task, logs, date_range)

    result = {"tasks": {}, "subtasks": {}}
    for s in task_stats:
        result["tasks"][s["id"]] = s["streak"]
        for ss in s["subtasks"]:
            result["subtasks"][ss["id"]] = ss["streak"]

    overall_day = _aggregate_day_status([s["daily_results"] for s in task_stats], date_range)
    result["overall"] = _compute_streak(sorted(overall_day.keys()), overall_day)
    return jsonify(result)

# ── API: REPORT ───────────────────────────────────────────────────────────────

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
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    habits_by_id = {h.id: h for h in habits}
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

    relevant_task_ids = [t.id for t in relevant_tasks]
    subtasks = Subtask.query.filter(Subtask.task_id.in_(relevant_task_ids)).all() if relevant_task_ids else []
    subtasks_by_task = defaultdict(list)
    for s in subtasks:
        subtasks_by_task[s.task_id].append(s)

    task_stats = _build_task_stats(relevant_tasks, subtasks_by_task, logs, date_range)
    habit_summary = _build_habit_summary(task_stats, habits_by_id, date_range)

    overall_day = _aggregate_day_status([s["daily_results"] for s in task_stats], date_range)
    overall_pct = (round(sum(s["success_pct"] for s in task_stats) / len(task_stats))
                   if task_stats else 0)
    overall_streak = _compute_streak(sorted(overall_day.keys()), overall_day)

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
        "habit_summary": habit_summary,
        "overall": {
            "pct": overall_pct,
            "day_status": overall_day,
            "total_tasks": len(task_stats),
            "streak": overall_streak,
        }
    })

# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(port=5050, debug=False)
