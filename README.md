# Robotics Team Ops MVP (Non-AI)

A focused, operational MVP for robotics/engineering team management.

## What this MVP now includes

- Email/password authentication and role routing (`member`, `leader`, `captain`)
- Member task view and weekly report submission (text + file + task rating 1-5)
- Leader department dashboard (members, task assignment, task status updates)
- Leader weekly project-linked reports to captain
- Leader weekly **project + department progress notes**
- Leader ability to remove only own-department members from active team membership
- Captain global controls:
  - assign tasks to any active non-captain user
  - update any task status
  - update any project status (`active`, `delayed`, `blocked`, `completed`, `on hold`)
  - update user role + department
  - view/edit/delete all reports
  - filter task table by department / project / status
  - view project breakdown by department with latest weekly notes
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

- `User`: name, email, role, department, password hash, active flag
- `Project`: name, description, status
- `ProjectDepartment`: project-to-department mapping
- `Task`: project, assignee, assigner, deadline, status, optional attachment
- `Report`: member/leader report, optional task, optional project, optional rating, attachment
- `DepartmentProgressNote`: weekly note per project + department by leader

## Quick setup

1. Create and activate venv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize fresh database:

```bash
flask --app app.py init-db
```

4. Run:

```bash
flask --app app.py run --debug
```

Open `http://127.0.0.1:5000`.

## Seed data

`init-db` creates a fresh clean starting state:

- 30 users total
  - 1 captain
  - 3 leaders (Mechanical, Electronics, Software)
  - 26 members distributed across Mechanical/Electronics/Software
- projects + project-department mappings
- **no initial tasks**
- **no initial reports**

Default password for all demo users:

```text
password123
```

## Permission rules

Members:
- only see their own tasks
- submit own reports with optional file and task rating

Leaders:
- see only own department members
- assign tasks only to own department members
- update task statuses only for own department members
- submit weekly project-linked leader reports
- submit weekly project-department progress notes
- remove only own department members (deactivate)

Captain:
- sees/manages all users, projects, tasks, reports
- can update any task status
- can edit project status
- can edit/delete reports
- can update user role and department
- can view member task ratings
- can view project breakdown with all core departments and latest notes

## Notes

- This release is still intentionally non-AI.
- Uploaded files are stored in `uploads/` and served via authenticated route.
