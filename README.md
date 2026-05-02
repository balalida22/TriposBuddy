# TriposBuddy

A multiuser past-paper tracking web app for Cambridge IA Engineering students.

Each student marks their own tripos questions as solved or unsolved. Groups let you see how your peers are progressing — a heatmap shows the group's collective solve rate per question, and hovering a cell reveals exactly who has solved it.

Deployed on [SRCF](https://www.srcf.net) (Student-Run Computing Facility).

---

## Features

**Personal tracker**
- 4 sections: 1P1, 1P2, 1P3, 1P4
- 12 questions × 10 years (2016–2025) per section
- Click any cell to toggle solved / unsolved — no page reload (HTMX)

**Groups**
- Create a group, invite others, or join public groups from the Discover page
- Private groups are accessible only via direct URL
- Two join modes: auto-approve or admin approval
- Group admins can promote/demote members and manage join requests

**Group heatmap**
- Cell fill: linear gradient from white (0%) to green (≥ threshold of group solved)
- Cell border: green when *you* have solved that question
- Hover to see which specific members solved it
- Saturation threshold configurable per group (default: 2/3)

**Admin panel** (root admin only)
- Generate and revoke invite links
- Reset user passwords, delete accounts
- Delete groups
- Add or remove individual questions from the matrix

**Settings**
- Change display username (default: CRSID)
- Change password
- Dark mode

**Auth**
- Registration requires an invite link + `@cam.ac.uk` email
- CSRF protection on all forms and HTMX requests

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13 · Flask 3 |
| Database | PostgreSQL · Flask-SQLAlchemy · Flask-Migrate |
| Auth | Flask-Login · Flask-Bcrypt · Flask-WTF |
| Frontend | HTMX 1.9 (CDN) · Jinja2 · plain CSS |
| Deployment | SRCF · Apache + Passenger WSGI |
| Local dev | uv |

---

## Local Development

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or see uv docs)
- PostgreSQL **or** use SQLite (zero setup, see below)

### Setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd TriposBuddy

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
```

Edit `.env`:

```bash
# SQLite (simplest — no database install needed)
DATABASE_URL=sqlite:///triposbuddy.db

# OR local PostgreSQL
# DATABASE_URL=postgresql://localhost/triposbuddy_dev

SECRET_KEY=change-me-to-a-long-random-string
FLASK_ENV=development
```

### Database initialisation

```bash
flask db upgrade          # applies migrations (creates all tables)
flask seed-questions      # populates 480 default questions (4×12×10)
flask create-admin you@cam.ac.uk yourusername yourpassword
```

### Run

```bash
flask run
# → http://127.0.0.1:5000
```

Log in with the admin account, then go to **Admin → Invites → Generate** to create an invite link for registering additional users.

---

## SRCF Deployment

```bash
# SSH into your SRCF shell
ssh crsid@shell.srcf.net

cd ~/public_html
git clone <your-repo-url> triposbuddy
cd triposbuddy

# Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env   # fill in SRCF credentials (see below)
```

SRCF `.env`:

```bash
DATABASE_URL=postgresql://CRSID:YOUR_DB_PASSWORD@postgres/CRSID
SECRET_KEY=<long-random-string>
FLASK_ENV=production
```

Your SRCF PostgreSQL password is in the [control panel](https://control.srcf.net). The hostname is always `postgres`.

```bash
# Run migrations and seed on SRCF
flask db upgrade
flask seed-questions
flask create-admin you@cam.ac.uk yourusername yourpassword
```

Passenger picks up `passenger_wsgi.py` automatically. Apache is configured via `.htaccess` in `public_html/`.

---

## Project Structure

```
TriposBuddy/
├── passenger_wsgi.py        # WSGI entry point (SRCF)
├── requirements.txt         # uv-compiled lockfile (pip-compatible)
├── .env.example             # environment variable template
│
└── app/
    ├── __init__.py          # app factory + CLI commands
    ├── models.py            # all SQLAlchemy models
    ├── config.py            # dev / prod config
    ├── extensions.py        # extension singletons
    │
    ├── auth/                # /auth — login, logout, register
    ├── tracker/             # /tracker — personal question tracker
    ├── groups/              # /groups — groups, heatmap, membership
    ├── settings/            # /settings — profile, password, dark mode
    ├── admin/               # /admin — root admin panel
    ├── notifications/       # /notifications — HTMX polling banner
    │
    ├── templates/           # Jinja2 templates
    └── static/css/          # main.css (CSS custom properties + dark mode)
```

See [`PROJECT_INDEX.md`](PROJECT_INDEX.md) for the full URL map, model schema, and HTMX patterns.

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `flask db upgrade` | Apply all pending migrations |
| `flask seed-questions` | Populate default 480 questions |
| `flask create-admin EMAIL USER PW` | Create the root admin account |

---

## Adding New Dependencies

```bash
# Add to requirements.txt, then recompile the lockfile
uv pip compile requirements.txt -o requirements.txt
uv pip install -r requirements.txt
```

On SRCF deployment, `pip install -r requirements.txt` consumes the same lockfile.
