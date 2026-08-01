# TaskFlow

A multi-user habit and task tracker. Each person gets their own account and their own private set of tasks/logs. Runs in the browser, backed by Postgres, deployable for free.

---

## What it does

**Manage Tasks** — Define tasks by category (Physical, Mental, Work, etc.), set how many times a day each must be done, and optionally add sub-tasks and descriptions.

**Daily Tracker** — Every day, check off each task as you do it. Tasks with a frequency of 2×/day show two checkboxes. A live progress bar shows how your day is going.

**Reports** — See your consistency over any past week or month. Navigate back in time with Prev/Next. Three views: overall score, per-category breakdown, and per-task heatmaps + bar charts.

**Accounts** — Register with an email + password. All tasks and logs are scoped to your account, so multiple people can share one deployment without seeing each other's data.

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
git clone https://github.com/Aarsh-J/TaskFlow.git
cd TaskFlow

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

---

## Running with Docker

```bash
docker build -t taskflow .
docker run -p 8080:8080 -e DATABASE_URL="postgresql://..." -e SECRET_KEY="..." taskflow
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
- Each account's tasks and logs are completely private to that account

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

## Project structure

```
TaskFlow/
├── run.py              ← Local dev entrypoint
├── app.py              ← Flask app + all API routes
├── auth.py             ← Register/login/logout routes
├── models.py            ← SQLAlchemy models (User, Task, Log)
├── migrations/          ← Alembic schema migrations
├── Dockerfile           ← Production container image
└── templates/
    ├── index.html      ← Base layout (nav, shared styles + JS)
    ├── login.html       ← Login page
    ├── register.html    ← Registration page
    ├── manage.html      ← Manage Tasks page
    ├── tracker.html     ← Daily Tracker page
    └── report.html      ← Reports page
```
