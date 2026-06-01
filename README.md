# Report Card Cameroon

A complete Django-based report card and transcript management system for secondary and high schools in Cameroon.

## Features

### Role-Based Access
| Role | Capabilities |
|------|-------------|
| **School Admin** | Create users, manage classes/subjects, generate transcripts |
| **Principal** | Validate report cards, grant print permissions, configure terms, manage classes/subjects, generate transcripts, create users |
| **Vice Principal** (max 2 per school) | Same privileges as Principal |
| **Class Master** | Enter marks, view class statistics/rankings, manage class subjects, add co-curricular activities |
| **Teacher** | Enter marks for assigned subjects only |
| **Student** | View report cards and transcripts (time-gated after term closing) |

### Core Workflow
1. **Principal configures term** — sets closing date, closing time (default 3:30 PM), and marks submission deadline (max 3 days before closing)
2. **Class master assigns subjects** to their class (especially for high school series A1-A4, S1-S4)
3. **Teachers upload marks** before the deadline — marks are locked after deadline
4. **Class master reviews statistics** — averages, rankings, grade distribution
5. **Principal validates report cards** between deadline and closing day
6. **Principal grants print permission** for hard-copy printing
7. **Students view report cards** after 3:30 PM on closing day (time-gated)

### Series Support (Cameroon System)
- **Form 1–5**: All 14 core subjects (Maths, English, French, Geography, Biology, Chemistry, Physics, Sports, Manual Labour, Home Economics, History, Citizenship, Religious Studies, Computer)
- **Lower Sixth & Upper Sixth**: Arts (A1–A4) and Sciences (S1–S4) with class-specific subject assignments managed by the class master

### Additional Features
- Transcript generation (by admin) and validation (by principal/VP)
- Co-curricular activity management per class
- Password reset via email
- PostgreSQL or SQLite support

---

## Tech Stack

- **Python** 3.14
- **Django** 6.0.5
- **PostgreSQL** (production) / **SQLite** (development)
- **WhiteNoise** for static files
- **Gunicorn** for production WSGI

---

## Quick Start

```powershell
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
copy .env.example .env

# 4. Edit .env with your settings:
#    - Set SECRET_KEY
#    - Set DEBUG=True for local
#    - Remove DATABASE_* lines to use SQLite, or configure PostgreSQL

# 5. Run migrations
python manage.py migrate

# 6. Seed test data (optional)
python manage.py seed

# 7. Create superuser (if not seeding)
python manage.py createsuperuser

# 8. Start server
python manage.py runserver
```

Open **http://127.0.0.1:8000/accounts/login/**

---

## Test Accounts (after `python manage.py seed`)

| Role | Username | Password |
|------|----------|----------|
| Superuser | `admin` | `admin123` |
| Principal | `principal1` | `pass123` |
| Vice Principal | `vice1` | `pass123` |
| Class Master | `master1` | `pass123` |
| Teacher | `teacher1` | `pass123` |
| Student | `student1` | `pass123` |

---

## All Pages

| Page | URL | Access |
|------|-----|--------|
| Login | `/accounts/login/` | All |
| Dashboard | `/accounts/dashboard/` | All |
| Enter Marks | `/accounts/enter-mark/` | Teacher, Class Master |
| Class Statistics | `/accounts/class-statistics/` | Class Master |
| Class Activities | `/accounts/class-activities/` | Class Master |
| Class Subjects | `/accounts/manage-class-subjects/` | Class Master |
| Validate Report Cards | `/accounts/validate-reportcards/` | Principal, VP |
| Print Permissions | `/accounts/grant-print-permission/` | Principal, VP |
| Term Settings | `/accounts/configure-term/` | Principal, VP |
| Create User | `/accounts/create-user/` | Admin, Principal, VP |
| Manage Classes | `/accounts/manage-classes/` | Admin, Principal, VP |
| Manage Subjects | `/accounts/manage-subjects/` | Admin, Principal, VP |
| Manage Transcripts | `/accounts/manage-transcripts/` | Admin, Principal, VP |
| My Report Card | `/accounts/my-reportcard/` | Student |
| My Transcript | `/accounts/my-transcript/` | Student |
| Admin Panel | `/admin/` | Superuser |

---

## Environment Variables (.env)

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (remove/comment out to use SQLite)
DATABASE_NAME=reportcard_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

---

## Production Deployment

### Option 1: Render (Easiest)

1. Push to GitHub
2. Connect repo to [Render](https://render.com)
3. Set build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Set start command: `gunicorn config.wsgi:application`
5. Add environment variables in Render dashboard

### Option 2: PythonAnywhere

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide.

### Option 3: Railway / Heroku

The `Procfile` and `runtime.txt` are pre-configured for Heroku-style platforms.

---

## Commands

```powershell
python manage.py check              # Run system checks
python manage.py migrate            # Apply migrations
python manage.py seed               # Seed test data
python manage.py createsuperuser    # Create admin user
python manage.py collectstatic      # Collect static files
python manage.py test               # Run tests
```

---

## Project Structure

```
reportcard_cameroon/
├── accounts/                    # Main application
│   ├── models.py               # All models (User, School, Class, Mark, ReportCard, Transcript, etc.)
│   ├── views.py                # All views (auth, marks, validation, statistics, transcripts)
│   ├── forms.py                # Forms (login, create user, mark entry, term config)
│   ├── services.py             # Business logic (mark submission, deadline checks)
│   ├── decorators.py           # Role-based access control
│   ├── urls.py                 # URL routing
│   ├── admin.py                # Admin panel registration
│   ├── management/commands/    # Custom management commands (seed)
│   ├── templates/accounts/     # HTML templates
│   └── migrations/             # Database migrations
├── config/                     # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── .env                        # Environment variables (git-ignored)
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── Procfile                    # Deployment config
├── runtime.txt                 # Python version
├── DEPLOYMENT.md               # Detailed deployment guide
└── manage.py                   # Django CLI
```

---

## Troubleshooting

**403 Forbidden when entering marks**: Ensure the user's role matches (`teacher` or `class_master`). Access is role-based, not permission-based.

**Marks deadline locked**: The principal must set a `marks_deadline` in Term Settings (max 3 days before closing date). After the deadline, marks cannot be modified.

**Student cannot view report card**: Report cards are only visible after 3:30 PM on the term closing date configured by the principal.

**Class master sees no statistics**: The class master must be assigned to a class via Manage Classes, and students must have marks entered.

**Database connection refused**: Check PostgreSQL is running, or comment out `DATABASE_*` in `.env` to use SQLite.

**Static files not loading**: Run `python manage.py collectstatic --noinput`.
