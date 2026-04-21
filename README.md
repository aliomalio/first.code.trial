# Robotics Team Ops MVP (Non-AI)

A focused, operational MVP for robotics/engineering team management.

## What this MVP includes

- Email/password authentication and role routing (`member`, `leader`, `captain`)
- Member task view and weekly report submission (text + file + task rating 1-5)
- Leader department dashboard (members, task assignment, task status updates)
- Leader weekly project-linked reports to captain
- Leader weekly **project + department progress notes** with optional file attachments
- Leader ability to remove only own-department members from active team membership
- Captain controls:
  - assign tasks to any active non-captain user
  - update any task status (`active`, `delayed`, `cancelled`, `done`)
  - update user role + department
  - remove users from team
  - filter task table by department / project / status
  - view/edit/delete all reports and filter by report type / department / project / author
  - view full project breakdown across Mechanical/Electronics/Software/Corporate
- File uploads for tasks and reports

## Tech stack

- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- Jinja templates + CSS

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

## Seed data (fresh clean system)

`init-db` creates:

- 30 users total
  - 1 captain
  - 4 leaders (Mechanical, Electronics, Software, Corporate)
  - 25 members distributed across all four departments
- 5 projects
  - Mecanum
  - Robotic Arm
  - Robotic Hand
  - Robotic Dog
  - Corporate Operations
- Project-department mappings for all departments on all projects
- No initial tasks
- No initial reports

Default password for all demo users:

```text
password123
```

## Demo login emails

Captain:
- `captain@enro`

Leaders:
- `m.leader@enro`
- `e.leader@enro`
- `s.leader@enro`
- `c.leader@enro`

Members:
- Mechanical: `m.member.1@enro` ... `m.member.7@enro`
- Electronics: `e.member.1@enro` ... `e.member.6@enro`
- Software: `s.member.1@enro` ... `s.member.6@enro`
- Corporate: `c.member.1@enro` ... `c.member.6@enro`

## Notes

- This release is intentionally non-AI.
- Uploaded files are stored in `uploads/` and served via authenticated route.
