# Hatchabit — UI/UX Polish + Automated Tests

## Context

Hatchabit is a Flask habit/task/subtask tracker, recently migrated to multi-user Postgres with auth and rebranded. The dark-themed dashboard UI (custom CSS variables, Syne/DM Sans/DM Mono fonts, card-based layout) is already visually decent, but everything is inline: no `static/` folder exists, all CSS/JS lives in `<style>`/`<script>` blocks inside Jinja templates, `manage.html` and `report.html` build DOM via `innerHTML` template strings with scattered inline `style="..."` attributes (19 and 31 occurrences respectively), and `report.html`'s charts are hand-rolled CSS bars. There's also zero test coverage anywhere in the repo. The goal is to make the app read as a polished, professional resume/portfolio piece: clean separation of concerns, a working theme toggle, a real charting library, better accessibility/responsiveness, and a focused automated test suite — without a full visual redesign or a backend architecture rewrite (both explicitly out of scope per your choices).

**Explicitly out of scope:** full visual redesign, `app.py` blueprint/service-layer refactor, README changes, deployment/CI changes, converting the calendar heatmap to Chart.js, rewriting `innerHTML` template-string rendering to `createElement`/DOM APIs.

## Phased approach

Do the mechanical, low-risk extraction first; save the riskier/rewrite-heavy work for later so each phase can be visually verified before the next begins.

### Phase 1 — Extract CSS into `static/css/`
Copy (not rewrite) the CSS out of `templates/index.html`'s `<style>` block and each page's `{% block extra_style %}` into files, preserving cascade order exactly:
- `variables.css` — `:root` custom properties (from `index.html:10-27`)
- `base.css` — resets, `body`, keyframes
- `layout.css` — `.shell`, `.topbar`, `.sidebar`, `.nav-*`, `.main`, `.menu-toggle`, `.sidebar-backdrop`, existing 768px media query
- `components.css` — `.card`, form styles, `.btn*`, `.heatmap`, `.bar-chart`, `.pct-badge`, `.stats-grid`, `.empty-state`, `.toast`, `.freq-badge`
- `pages/manage.css`, `pages/report.css`, `pages/tracker.css`, `pages/todo.css`, `pages/auth.css` — each page's `extra_style` content verbatim

`index.html`'s `<head>` links the four shared files in order, then `{% block extra_style %}` still exists for each page to link its own `pages/*.css` file. Zero visual diff expected — verify via the `run` skill (start the app, screenshot each of the 6 pages before/after).

### Phase 2 — Extract JS into `static/js/`
Same mechanical approach:
- `shared.js` — index.html's shared script body (`toast()`, `esc()`, `pctClass()`, `setBtnLoading()`, `freqLabel()`, topbar clock, mobile sidebar toggle)
- `pages/manage.js`, `pages/report.js`, `pages/tracker.js`, `pages/todo.js` — each page's `extra_script` content verbatim, loaded via `<script src>`

Functions stay on `window` scope as plain scripts (no ES modules), so existing `onclick="..."` attributes in generated HTML keep working unchanged. Zero behavioral diff expected.

### Phase 3 — Light/dark theme toggle
- Add `[data-theme="light"]` override block to `variables.css` (light bg/surface/border/text, keep accent colors, verify contrast — see Phase 5)
- Add a toggle button in the topbar next to `.topbar-date`, styled like the existing `.menu-toggle`
- Small inline snippet in `<head>` (before CSS links) reads `localStorage` and sets `data-theme` on `<html>` early to avoid a flash of wrong theme; click handler and persistence logic live in `shared.js`
- Default stays `dark` — no visual change for anyone who doesn't toggle

### Phase 4 — Chart.js migration (bar chart only)
- Add Chart.js via CDN `<script src="https://cdn.jsdelivr.net/npm/chart.js@4">` (no bundler — none exists in this project, adding one just for this would be disproportionate)
- Replace `barChart()` in `report.html`/`pages/report.js` (currently hand-built `.bar-chart`/`.bar-col`/`.bar` divs, `report.html:331-347`) with a `<canvas>` + `new Chart(ctx, {type:'bar', ...})`, using the exact same `{date: status}` data already returned by `GET /api/report` — **no backend changes needed**
- Render flow changes: string-render a `<canvas id="chart-...">` placeholder, then after `innerHTML` insertion, instantiate/`destroy()`-and-reinstantiate the Chart object per canvas
- **Leave the calendar heatmap (`heatmap()`/`heatmapWithLabels()`) as CSS grid** — no good Chart.js equivalent for a per-day tooltip calendar grid; forcing it would be a downgrade

### Phase 5 — Accessibility pass
- Associate existing `<label>` tags with their inputs via `for`/`id` (IDs mostly already exist for JS hooks — just add `for=`)
- Add `aria-label` alongside existing `title` attrs on icon-only buttons (edit/archive/delete in manage.html, prev/next nav arrows in report.html)
- Make report.html's clickable `type-card-header` divs keyboard-accessible: `role="button"`, `tabindex="0"`, `aria-expanded`, Enter/Space handler
- Add a global `:focus-visible` outline rule in `base.css` (currently only form inputs get a focus style)
- Check contrast of `--muted` (#6b7585) text on `--surface`/`--surface2` at small font sizes — likely borderline AA, lighten if it fails
- Mobile sidebar: move focus into sidebar on open, return focus to toggle on close, Escape-to-close, `aria-expanded` on the toggle button, prevent tabbing into off-screen sidebar links when closed

### Phase 6 — Responsive breakpoints
Add a second breakpoint (~480px) for phone-specific fixes not covered by the existing 768px rule:
- `report.html`: `.overall-card` stacks to single column, `.nav-row` shrinks/wraps, heatmap cells shrink slightly, chart canvas height reduces
- `manage.html`: `.form-row.three` needs its own collapse rule (currently only the base `.form-row` collapses at 768px), modal padding shrinks, long task names truncate/wrap cleanly

### Phase 7 — Inline `style=""` cleanup in manage.html and report.html
Convert the 19 (manage.html) + 31 (report.html) inline `style="..."` occurrences inside JS template-string literals into a small set of reusable utility classes (`.u-row`, `.u-row-between`, `.u-flex-1`, `.u-mt-8/12/16`, `.u-muted-xs`, etc.) added to `components.css`, since most occurrences are near-duplicate one-off layout tweaks. **Keep the `innerHTML`/template-string rendering approach as-is** — only swap `style="..."` for `class="..."`, don't rewrite to `createElement`. Lowest risk, most tedious phase — do last.

### Phase 8 — Automated tests
Setup blocker: `app.py` builds `app = Flask(__name__)` and reads `os.environ["SECRET_KEY"]`/`os.environ["DATABASE_URL"]` at import time, no factory function. Work around it (don't refactor `app.py`):
- `tests/conftest.py` sets those env vars (pointing `DATABASE_URL` at a throwaway SQLite temp file) **before** importing `app`, then provides `app`/`db`/`client` fixtures (function-scoped, `db.create_all()`/`drop_all()` per test) and a login helper that exercises the real `/register`+`/login` routes
- Add `pytest` to a new `requirements-dev.txt` (keep prod image lean)
- Test files, prioritized by value:
  1. `test_report.py` — **highest priority**: unit-test the aggregation helpers (`_week_bounds`, `_month_bounds`, `_compute_streak`, `_aggregate_day_status`) directly, plus an integration test seeding habits/tasks/logs and asserting on `GET /api/report`'s JSON shape — this locks in the contract the frontend (and new Chart.js code) depends on
  2. `test_auth.py` — register (valid/duplicate email/short password), login (correct/incorrect), logout, protected-route redirect
  3. `test_habits_tasks.py` — CRUD + archive/restore + cascade delete + cross-user ownership enforcement (security-relevant: verify a user can't edit another user's task)
  4. `test_tracker_logs.py` — log toggle idempotency, multi-occurrence logging for frequency>1 tasks, period-progress endpoint
  5. `test_todo.py` — brief CRUD coverage

Out of scope: JS unit tests, CI pipeline config, `app.py` factory refactor.

## Verification

- After Phases 1-2: run the app locally (`run` skill), visually compare all 6 pages against current screenshots — expect byte-for-byte identical rendering
- After Phase 3: toggle theme on each page, confirm persistence across reload/navigation, confirm default stays dark
- After Phase 4: load Reports page, confirm bar charts render identically in shape/color to before, confirm no console errors, test period navigation re-renders charts without leaking old Chart instances
- After Phase 5-6: keyboard-only navigation pass (tab through a full page, open/close mobile sidebar, expand a report card, submit a form) on a narrow viewport
- After Phase 8: `pytest` run, all tests green; spot-check that `test_report.py`'s integration test actually catches a deliberately-introduced bug (e.g. temporarily break `_compute_streak`) to confirm it's not a false-positive test

### Critical files
- `templates/index.html` — base layout, biggest source of CSS/JS to extract
- `templates/report.html` — most inline styles (31), chart migration target
- `templates/manage.html` — second-most inline styles (19)
- `app.py` — report aggregation logic (`_build_task_stats`, `_build_habit_summary`, `_aggregate_day_status`, `_compute_streak`), route definitions for test targets
- `models.py` — schema for test fixtures
