# Hatchabit

A multi-user habit and task tracker. Each person gets their own account and their own private set of habits/tasks/logs. Runs in the browser, backed by Postgres, deployable for free.

---

## What it does

**Manage Habits** — Group your routines under Habits (e.g. Physical Health, Work), each with a color. Under each Habit, add Tasks with how often they need doing — a number of times per **day**, **week**, or **month** (e.g. "2×/day", "3×/week", "20×/month"). Tasks can optionally have Sub-tasks, each with their own frequency and unit.

**Daily Tracker** — Every day, check off each task as you do it.
- Day-frequency tasks (e.g. 2×/day) show that many checkboxes, resetting each day.
- Week/month-frequency tasks show a single "done today" checkbox plus a running progress readout (e.g. "1/3 this week").
A live progress bar shows how your day is going.

**Reports** — See your consistency over any past week or month. Navigate back in time with Prev/Next. Three views: overall score, per-habit breakdown, and per-task heatmaps + bar charts. Day-frequency tasks are judged day by day; week/month-frequency tasks are judged once per period (a week isn't marked "missed" just because it isn't finished yet).

**To-do** — A separate one-off list (with optional deadlines) for things that aren't recurring habits, kept apart from the Daily Tracker.

**Accounts** — Register with an email + password. All habits, tasks, and logs are scoped to your account, so multiple people can share one deployment without seeing each other's data.

---

## Tech stack

- **Python + Flask** — backend and API
- **SQLAlchemy + Flask-Migrate** — ORM and schema migrations
- **PostgreSQL** (hosted on [Supabase](https://supabase.com), free tier) — data storage
- **Flask-Login + Werkzeug** — authentication and password hashing
- **Jinja2** — templating
- **Vanilla HTML / CSS / JS** — frontend, no frameworks
- **Docker + gunicorn** — containerized production server
- **Render** — hosting, auto-deploys on push to `main`

---

## Local development

**Requirements:** Python 3.10+, a Postgres database (e.g. a free [Supabase](https://supabase.com) project)

```bash
# 1. Clone the project
git clone https://github.com/Aarsh-J/Hatchabit.git
cd Hatchabit

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Create a .env file with:
#   DATABASE_URL="postgresql://..."
#   SECRET_KEY="<random secret>"

# 4. Apply database migrations
export FLASK_APP=app.py   # (Windows: set FLASK_APP=app.py)
flask db upgrade

# 5. Run
python run.py
```

The app opens automatically at `http://localhost:5050`. Register an account, then log in.

### Working against a separate dev database

To avoid touching prod data while developing, keep a second Postgres project (e.g. another free Supabase project) for local testing, with its credentials in `.env.dev` instead of `.env`. Two PowerShell launcher scripts pick which one to use without ever touching the other file:

```powershell
.\run-dev.ps1    # loads .env.dev, runs against the dev database
.\run-prod.ps1   # loads .env, runs against the real prod database — be careful
```

Both scripts set env vars directly in the process before starting `run.py`, so whichever one you run wins regardless of what's in the other file.

---

## Running with Docker

```bash
docker build -t hatchabit .
docker run -p 8080:8080 -e DATABASE_URL="postgresql://..." -e SECRET_KEY="..." hatchabit
```

The container runs pending migrations automatically on startup before serving requests.

---

## Deployment

Deployed on [Render](https://render.com) as a Docker-based web service, connected to this GitHub repo — every push to `main` triggers an automatic rebuild and redeploy. The database is a free Postgres instance on Supabase (Mumbai region, for low latency).

Required environment variables on the host:
- `DATABASE_URL` — Supabase Postgres connection string
- `SECRET_KEY` — random string used to sign session cookies

---

## How to use

### Register / Log In
- First visit redirects to `/login`; use the link there to `/register` a new account
- Each account's habits, tasks, and logs are completely private to that account

### Manage Habits
- Go to **Manage Habits** in the sidebar
- Create a Habit (name + description) to group related tasks
- Under a Habit, add a Task: name, description, and how often ("Times" + "Per: Day/Week/Month")
- Optionally add Sub-tasks under a Task, each with its own frequency and unit
- "Remove from routine" archives a task/sub-task (keeps its history for reports); the delete button removes it and its history permanently

### Daily Tracker
- Go to **Daily Tracker** — it defaults to today
- Use ← Prev / Next → to navigate to other days
- Day-frequency tasks: check off each numbered box as you complete each repetition
- Week/month-frequency tasks: check the single "today" box; the readout next to it shows cumulative progress for the current week/month
- A task is fully done when all its boxes are checked (green = done, yellow = partial)

### Reports
- Go to **Reports**
- Toggle between **Weekly** (Sun–Sat) and **Monthly**
- Use ← Prev / Next → to browse past periods
- Navigation is disabled for periods before your first task was created
- Three sections:
  - **Overall** — single % score, perfect/partial/missed day counts, best and worst task
  - **By Habit** — per-habit % and heatmap
  - **Task Breakdown** — collapsible cards with per-task heatmap and bar chart

### To-do
- Go to **To-do** for one-off items that aren't recurring habits
- Add a name, optional description, and optional deadline
- Check items off as done; overdue/upcoming deadlines are badged

---

## Project structure

```
Hatchabit/
├── run.py               ← Local dev entrypoint
├── run-dev.ps1           ← Launch locally against .env.dev (dev database)
├── run-prod.ps1          ← Launch locally against .env (prod database)
├── app.py                ← Flask app + all API routes
├── auth.py               ← Register/login/logout routes
├── models.py              ← SQLAlchemy models (User, Habit, Task, Subtask, Log, ToDo)
├── migrations/            ← Alembic schema migrations
├── Dockerfile             ← Production container image
└── templates/
    ├── index.html        ← Base layout (nav, shared styles + JS)
    ├── login.html         ← Login page
    ├── register.html      ← Registration page
    ├── manage.html        ← Manage Habits page
    ├── tracker.html       ← Daily Tracker page
    ├── report.html        ← Reports page
    └── todo.html          ← To-do page
```
