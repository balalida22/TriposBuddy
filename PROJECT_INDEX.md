# Project Index: TriposBuddy

Generated: 2026-05-02
Stack: Flask 3 · PostgreSQL · HTMX 1.9 · Jinja2 · Python 3.13

---

## 📁 Project Structure

```
TriposBuddy/
├── passenger_wsgi.py          # WSGI entry point (SRCF/Apache)
├── requirements.txt           # uv-compiled lockfile (pip-compatible)
├── .env.example               # env var template
│
└── app/
    ├── __init__.py            # App factory + CLI commands
    ├── config.py              # Dev / Prod config classes
    ├── extensions.py          # Extension singletons (db, bcrypt, etc.)
    ├── models.py              # All SQLAlchemy models
    │
    ├── auth/                  # Blueprint: /auth
    │   ├── forms.py           # LoginForm, RegisterForm (WTForms)
    │   └── routes.py          # login, logout, register
    │
    ├── tracker/               # Blueprint: /tracker
    │   └── routes.py          # Personal tracker + HTMX toggle
    │
    ├── groups/                # Blueprint: /groups
    │   ├── heatmap.py         # Solve-rate computation + colour math
    │   └── routes.py          # Full group CRUD, join/leave, heatmap
    │
    ├── settings/              # Blueprint: /settings
    │   └── routes.py          # Profile, password, dark mode
    │
    ├── admin/                 # Blueprint: /admin (root only)
    │   └── routes.py          # Users, invites, groups, questions
    │
    ├── notifications/         # Blueprint: /notifications
    │   └── routes.py          # HTMX poll + dismiss
    │
    ├── templates/
    │   ├── base.html          # Layout: nav, notification banner, CSRF meta
    │   ├── auth/              # login, register, invalid_invite
    │   ├── tracker/           # index, _cell (HTMX swap target)
    │   ├── groups/            # my_groups, discover, create, group_public,
    │   │                      #   group_member (heatmap), group_settings,
    │   │                      #   join_requests, leave_warning, _tooltip
    │   ├── settings/          # index
    │   ├── admin/             # index, users, invites, groups, questions
    │   └── notifications/     # _banner (HTMX partial)
    │
    └── static/
        └── css/main.css       # All styles + dark mode (CSS custom props)
```

---

## 🚀 Entry Points

| Entry | Path | Purpose |
|-------|------|---------|
| WSGI | `passenger_wsgi.py` | Apache/Passenger entry on SRCF |
| App factory | `app/__init__.py:create_app()` | Creates Flask app, registers all blueprints |
| CLI: seed | `flask seed-questions` | Populates 480 default questions |
| CLI: admin | `flask create-admin EMAIL USER PW` | Creates root admin user |
| Root redirect | `GET /` | → `/tracker` if logged in, else `/auth/login` |

---

## 📦 Core Modules

### `app/models.py`
All SQLAlchemy models. Key classes:

| Model | Purpose |
|-------|---------|
| `User` | Auth + profile. `is_root_admin` flag. Backref `memberships`, `notifications`, `progress` |
| `Invitation` | Single-use invite tokens. `.is_valid` property |
| `Question` | `(section, year, question_number)` unique. `.label` property |
| `UserQuestionProgress` | User × Question solved/unsolved record |
| `Group` | `.member_count`, `.admin_count` properties. `slug` unique |
| `GroupMembership` | User ↔ Group with `MemberRole` enum (admin/member) |
| `GroupJoinRequest` | Pending/approved/rejected join requests |
| `Notification` | In-app banners, `read` flag |

Enums: `SectionEnum` (1P1/1P2/1P3/1P4), `MemberRole`, `JoinRequestStatus`

### `app/groups/heatmap.py`
Heatmap computation — called on every group member page load.

| Function | Signature | Purpose |
|----------|-----------|---------|
| `compute_heatmap(group, viewer_user)` | → nested dict | Builds full section→year→q_num data with fill + border colours |
| `solve_fill_color(solved, total, threshold)` | → `rgb(r,g,b)` | Linear gradient white→#22c55e clamped at threshold |
| `get_cell_solvers(group, question_id)` | → `[str]` | Usernames of group members who solved a question |

### `app/auth/forms.py`
WTForms validators enforce `@cam.ac.uk` email and unique username at form level.

### `app/extensions.py`
Singletons: `db`, `migrate`, `login_manager`, `bcrypt`, `csrf`

---

## 🔧 Configuration

| File | Purpose |
|------|---------|
| `app/config.py` | `DevelopmentConfig` (DEBUG=True) / `ProductionConfig` (secure cookies). Selected via `FLASK_ENV` env var |
| `.env` (gitignored) | `SECRET_KEY`, `DATABASE_URL`, `FLASK_ENV` |
| `.env.example` | Template for above |

**Key env vars:**

```
SECRET_KEY=<64-char random string>
DATABASE_URL=postgresql://CRSID:PW@postgres/CRSID   # SRCF format
FLASK_ENV=production
```

---

## 🗺️ URL Map

```
GET  /                                    → redirect (tracker or login)

# Auth
GET/POST /auth/login
GET      /auth/logout
GET/POST /auth/register?token=<token>

# Tracker
GET  /tracker/                            # 4-section matrix page
POST /tracker/toggle                      # HTMX: toggle cell, returns _cell.html

# Groups
GET  /groups/                             # My groups
GET  /groups/discover
GET  /groups/new
POST /groups/new
GET  /groups/<slug>                       # Auto-switches: public view ↔ member+heatmap
POST /groups/<slug>/join
POST /groups/<slug>/leave
GET/POST /groups/<slug>/settings          # Group admin only
GET  /groups/<slug>/requests
POST /groups/<slug>/requests/<id>/approve
POST /groups/<slug>/requests/<id>/reject
POST /groups/<slug>/members/<id>/promote
POST /groups/<slug>/members/<id>/demote
POST /groups/<slug>/members/<id>/remove
GET  /groups/<slug>/heatmap/cell/<q_id>/solvers   # HTMX tooltip

# Settings
GET      /settings/
POST     /settings/profile
POST     /settings/password
POST     /settings/darkmode

# Admin (root only)
GET      /admin/
GET      /admin/users
POST     /admin/users/<id>/reset-password
POST     /admin/users/<id>/delete
GET      /admin/invites
POST     /admin/invites/generate
POST     /admin/invites/<id>/revoke
GET      /admin/groups
POST     /admin/groups/<id>/delete
GET      /admin/questions
POST     /admin/questions/add
POST     /admin/questions/<id>/delete

# Notifications
GET  /notifications/poll                  # HTMX polled every 30s
POST /notifications/<id>/dismiss
```

---

## 🗄️ Database Schema (summary)

```
users              (id, email, username, password_hash, is_root_admin, dark_mode)
invitations        (id, token[unique], created_by→users, used_by→users, revoked)
questions          (id, section[enum], year, question_number) UNIQUE(section,year,q_num)
user_question_progress  (user_id→users, question_id→questions, solved, solved_at) UNIQUE(user,q)
groups             (id, name, slug[unique], description, is_public, auto_approve,
                    sat_threshold, created_by→users)
group_memberships  (group_id→groups, user_id→users, role[enum]) UNIQUE(group,user)
group_join_requests(group_id, user_id, status[enum], resolved_by→users)
notifications      (user_id→users, message, read)
```

Cascade deletes: user deletion cascades to progress, memberships, join requests, notifications.
Group deletion cascades to memberships, join requests.

---

## 🎨 Frontend Architecture

- **No JS framework.** HTMX handles all dynamic updates.
- **CSRF:** Meta tag in `base.html` + `htmx:configRequest` listener injects `X-CSRFToken` header on every HTMX request.
- **Dark mode:** `<html data-theme="dark|light">` toggled server-side; CSS custom properties in `main.css` handle all theming.
- **Heatmap tooltip:** HTMX `hx-trigger="mouseenter"` fetches solver list; positioned via inline JS `showTooltip(event)`.
- **Notification banner:** HTMX polls `/notifications/poll` on load and every 30s; auto-dismisses after 5s via `setTimeout`.

---

## 🔒 Security Notes

| Concern | Implementation |
|---------|---------------|
| Passwords | `bcrypt` via Flask-Bcrypt |
| Sessions | `SECRET_KEY` from env; `SESSION_COOKIE_SECURE=True` in prod |
| CSRF | Flask-WTF on all forms; HTMX uses `X-CSRFToken` header |
| Invite tokens | `secrets.token_urlsafe(32)`, single-use, revocable |
| Root admin guard | `require_root_admin` decorator on all `/admin/*` routes |
| Group data guard | Membership check before every group heatmap/member view |
| Email restriction | Server-side `@cam.ac.uk` check in `RegisterForm.validate_email` |

---

## 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.3 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Migrate | 4.0.7 | Alembic migrations |
| Flask-Login | 0.6.3 | Session auth |
| Flask-Bcrypt | 1.0.1 | Password hashing |
| Flask-WTF | 1.2.1 | CSRF + form validation |
| psycopg2-binary | 2.9.10 | PostgreSQL driver (Python 3.13 compatible) |
| gunicorn | 22.0.0 | WSGI server (local/alt deployment) |
| HTMX | 1.9.12 | CDN, dynamic updates (no JS framework) |

---

## ⚙️ Dependency Management

- **Local dev:** `uv` — lockfile managed via `uv pip compile`
- **SRCF deployment:** `pip install -r requirements.txt` inside a `venv`
- To add a dep: edit `requirements.txt`, then `uv pip compile requirements.txt -o requirements.txt`

---

## 🚀 Quick Start

```bash
# 1. Install deps (local)
uv pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env   # fill in SECRET_KEY and DATABASE_URL

# 3. Init + migrate DB
flask db init
flask db migrate -m "init"
flask db upgrade

# 4. Seed questions (480 defaults)
flask seed-questions

# 5. Create root admin
flask create-admin you@cam.ac.uk yourusername yourpassword

# 6. Run locally
flask run
```

---

## 🏗️ SRCF Deployment

```bash
# On SRCF shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up .env with SRCF postgres credentials
# Apache reads passenger_wsgi.py via .htaccess PassengerEnabled
```

See `.env.example` for SRCF-specific `DATABASE_URL` format (`postgresql://CRSID:PW@postgres/CRSID`).
