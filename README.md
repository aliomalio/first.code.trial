# Robotics Team Ops MVP (Non-AI)

A first operational MVP for a robotics/engineering team management web app.

## What this MVP includes

- Email/password authentication
- Role-based dashboards (`member`, `leader`, `captain`)
- Department-aware task assignment
- Project-linked tasks
- Weekly reports from members and leaders
- Report submission tracking for leaders (who submitted this week / who did not)
- Captain global visibility across teams, projects, tasks, and reports
- File uploads for tasks and reports

## Tech stack

- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- Jinja templates + CSS

## Project structure

```text
.
├── app.py
├── requirements.txt
├── app.db (generated after init)
├── uploads/ (generated automatically)
├── static/
│   └── styles.css
└── templates/
    ├── base.html
    ├── login.html
    ├── member_dashboard.html
    ├── leader_dashboard.html
    └── captain_dashboard.html
```

## Data model overview

- `User`: name, email, role, department, password hash
- `Project`: name, description, status
- `ProjectDepartment`: many-to-many style mapping of project-to-department
- `Task`: linked to project, assignee, assigner, deadline, status, optional attachment
- `Report`: member/leader report, optional task link, optional attachment

## Quick setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize database with demo data:

```bash
flask --app app.py init-db
```

4. Run the app:

```bash
flask --app app.py run --debug
```

Open: `http://127.0.0.1:5000`

## Demo logins (all use same password)

Password for all users:

```text
password123
```

Users:

- Captain: `captain@robotics.local`
- Mechanical Leader: `leader.mech@robotics.local`
- Electronics Leader: `leader.elec@robotics.local`
- Software Leader: `leader.soft@robotics.local`
- Mechanical Member: `member.mech@robotics.local`
- Electronics Member: `member.elec@robotics.local`
- Software Member: `member.soft@robotics.local`
- Corporate Member: `member.corp@robotics.local`

## Core workflow supported

1. User logs in.
2. User is redirected to role dashboard.
3. Leader creates and assigns task to own-department members.
4. Member sees assigned task.
5. Member submits weekly report (with optional file).
6. Leader sees missing report list for current week.
7. Leader submits leader report to captain view.
8. Captain monitors all users, projects, tasks, reports, and project/department breakdown.

## Notes

- This version intentionally excludes all AI features.
- File uploads are saved in local `uploads/` and served through authenticated route.
