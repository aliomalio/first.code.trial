from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

ROLE_OPTIONS = ["member", "leader", "captain"]
DEPARTMENT_OPTIONS = ["Mechanical", "Electronics", "Software", "Corporate"]
TASK_STATUS_OPTIONS = ["active", "delayed", "cancelled", "done"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-me"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'app.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

UPLOAD_DIR.mkdir(exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    assigned_tasks = db.relationship("Task", foreign_keys="Task.assigned_to_id", backref="assignee")
    created_tasks = db.relationship("Task", foreign_keys="Task.assigned_by_id", backref="assigner")
    reports = db.relationship("Report", backref="author")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ProjectDepartment(db.Model):
    __tablename__ = "project_departments"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    department = db.Column(db.String(50), nullable=False)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="active")

    tasks = db.relationship("Task", backref="project")
    departments = db.relationship("ProjectDepartment", backref="project", cascade="all, delete")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    reports = db.relationship("Report", backref="related_task")


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    related_task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
    report_type = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    task_rating = db.Column(db.Integer, nullable=True)
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    project = db.relationship("Project")


class DepartmentProgressNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    note = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    project = db.relationship("Project")
    leader = db.relationship("User")


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def role_required(*allowed_roles):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in allowed_roles:
                flash("You do not have access to this page.", "error")
                return redirect(url_for("dashboard"))
            return func(*args, **kwargs)

        return inner

    return wrapper


def save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    name = secure_filename(file_storage.filename)
    final_name = f"{uuid4().hex}_{name}"
    file_storage.save(UPLOAD_DIR / final_name)
    return final_name


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def eligible_projects_for_department(department: str):
    return (
        Project.query.join(ProjectDepartment, ProjectDepartment.project_id == Project.id)
        .filter(ProjectDepartment.department == department)
        .order_by(Project.name.asc())
        .all()
    )


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials or inactive user.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "member":
        return redirect(url_for("member_dashboard"))
    if current_user.role == "leader":
        return redirect(url_for("leader_dashboard"))
    return redirect(url_for("captain_dashboard"))


@app.route("/member", methods=["GET", "POST"])
@login_required
@role_required("member")
def member_dashboard():
    tasks = (
        Task.query.filter_by(assigned_to_id=current_user.id)
        .order_by(Task.deadline.asc(), Task.created_at.desc())
        .all()
    )

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        task_id = request.form.get("task_id") or None
        rating = request.form.get("task_rating")

        if not text:
            flash("Report text is required.", "error")
        elif not rating or int(rating) not in [1, 2, 3, 4, 5]:
            flash("Task rating (1-5) is required.", "error")
        elif task_id and not any(t.id == int(task_id) for t in tasks):
            flash("You can only report on your own tasks.", "error")
        else:
            attachment = save_upload(request.files.get("attachment"))
            related_task = db.session.get(Task, int(task_id)) if task_id else None
            report = Report(
                author_id=current_user.id,
                related_task_id=related_task.id if related_task else None,
                project_id=related_task.project_id if related_task else None,
                report_type="member",
                text=text,
                task_rating=int(rating),
                attachment_path=attachment,
            )
            db.session.add(report)
            db.session.commit()
            flash("Weekly report submitted.", "success")
            return redirect(url_for("member_dashboard"))

    reports = Report.query.filter_by(author_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("member_dashboard.html", tasks=tasks, reports=reports)


@app.route("/leader", methods=["GET", "POST"])
@login_required
@role_required("leader")
def leader_dashboard():
    members = (
        User.query.filter_by(role="member", department=current_user.department, is_active=True)
        .order_by(User.name.asc())
        .all()
    )
    member_ids = [m.id for m in members]
    member_tasks = (
        Task.query.filter(Task.assigned_to_id.in_(member_ids) if member_ids else False)
        .order_by(Task.deadline.asc())
        .all()
    )
    projects = eligible_projects_for_department(current_user.department)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_task":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            project_id = request.form.get("project_id")
            deadline_str = request.form.get("deadline")
            assigned_to_id = request.form.get("assigned_to_id")
            member = db.session.get(User, int(assigned_to_id)) if assigned_to_id else None
            project = db.session.get(Project, int(project_id)) if project_id else None

            if not all([title, description, project_id, deadline_str, assigned_to_id]):
                flash("Please fill all task fields.", "error")
            elif not member or member.department != current_user.department or member.role != "member":
                flash("You can assign tasks only to active members in your own department.", "error")
            elif not project or current_user.department not in [d.department for d in project.departments]:
                flash("You can assign only projects relevant to your department.", "error")
            else:
                attachment = save_upload(request.files.get("task_attachment"))
                task = Task(
                    title=title,
                    description=description,
                    project_id=project.id,
                    assigned_to_id=member.id,
                    assigned_by_id=current_user.id,
                    deadline=datetime.strptime(deadline_str, "%Y-%m-%d").date(),
                    status="active",
                    attachment_path=attachment,
                )
                db.session.add(task)
                db.session.commit()
                flash("Task assigned.", "success")
                return redirect(url_for("leader_dashboard"))

        elif action == "update_task_status":
            task_id = request.form.get("task_id")
            status = request.form.get("status")
            task = db.session.get(Task, int(task_id)) if task_id else None
            if not task or task.assignee.department != current_user.department:
                flash("You can only update tasks for your department members.", "error")
            elif status not in TASK_STATUS_OPTIONS:
                flash("Invalid task status.", "error")
            else:
                task.status = status
                db.session.commit()
                flash("Task status updated.", "success")
                return redirect(url_for("leader_dashboard"))

        elif action == "submit_report":
            text = request.form.get("text", "").strip()
            project_id = request.form.get("project_id")
            project = db.session.get(Project, int(project_id)) if project_id else None
            if not text or not project_id:
                flash("Project and report text are required.", "error")
            elif not project or current_user.department not in [d.department for d in project.departments]:
                flash("Selected project is not valid for your department.", "error")
            else:
                attachment = save_upload(request.files.get("leader_attachment"))
                report = Report(
                    author_id=current_user.id,
                    project_id=project.id,
                    report_type="leader",
                    text=text,
                    attachment_path=attachment,
                )
                db.session.add(report)
                db.session.commit()
                flash("Leader weekly report submitted.", "success")
                return redirect(url_for("leader_dashboard"))

        elif action == "submit_progress_note":
            project_id = request.form.get("project_id")
            note_text = request.form.get("note", "").strip()
            project = db.session.get(Project, int(project_id)) if project_id else None
            if not project or not note_text:
                flash("Project and note text are required.", "error")
            elif current_user.department not in [d.department for d in project.departments]:
                flash("Selected project is not valid for your department.", "error")
            else:
                week_start = current_week_start()
                attachment = save_upload(request.files.get("progress_attachment"))
                existing = DepartmentProgressNote.query.filter_by(
                    project_id=project.id,
                    department=current_user.department,
                    week_start=week_start,
                ).first()
                if existing:
                    existing.note = note_text
                    existing.leader_id = current_user.id
                    if attachment:
                        existing.attachment_path = attachment
                else:
                    db.session.add(
                        DepartmentProgressNote(
                            project_id=project.id,
                            department=current_user.department,
                            leader_id=current_user.id,
                            week_start=week_start,
                            note=note_text,
                            attachment_path=attachment,
                        )
                    )
                db.session.commit()
                flash("Weekly project-department progress note saved.", "success")
                return redirect(url_for("leader_dashboard"))

        elif action == "remove_member":
            member_id = request.form.get("member_id")
            member = db.session.get(User, int(member_id)) if member_id else None
            if not member or member.role != "member" or member.department != current_user.department:
                flash("You can only remove members from your own department.", "error")
            else:
                member.is_active = False
                db.session.commit()
                flash(f"{member.name} removed from active team membership.", "success")
                return redirect(url_for("leader_dashboard"))

    tasks_by_member = {}
    for t in member_tasks:
        tasks_by_member.setdefault(t.assigned_to_id, []).append(t)

    week_start_dt = datetime.combine(current_week_start(), datetime.min.time())
    recent_reports = (
        Report.query.filter(Report.author_id.in_(member_ids) if member_ids else False)
        .filter(Report.report_type == "member")
        .filter(Report.created_at >= week_start_dt)
        .all()
    )
    submitted_member_ids = {r.author_id for r in recent_reports}
    missing_reports = [m for m in members if m.id not in submitted_member_ids]

    leader_reports = (
        Report.query.filter_by(author_id=current_user.id, report_type="leader")
        .order_by(Report.created_at.desc())
        .all()
    )

    progress_notes = (
        DepartmentProgressNote.query.filter_by(department=current_user.department)
        .order_by(DepartmentProgressNote.week_start.desc(), DepartmentProgressNote.created_at.desc())
        .all()
    )

    return render_template(
        "leader_dashboard.html",
        members=members,
        tasks_by_member=tasks_by_member,
        projects=projects,
        missing_reports=missing_reports,
        leader_reports=leader_reports,
        week_start=current_week_start(),
        task_status_options=TASK_STATUS_OPTIONS,
        progress_notes=progress_notes,
    )


@app.route("/captain", methods=["GET", "POST"])
@login_required
@role_required("captain")
def captain_dashboard():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "assign_task":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            project_id = request.form.get("project_id")
            deadline_str = request.form.get("deadline")
            assigned_to_id = request.form.get("assigned_to_id")
            if not all([title, description, project_id, deadline_str, assigned_to_id]):
                flash("Please fill all task fields.", "error")
            else:
                attachment = save_upload(request.files.get("task_attachment"))
                task = Task(
                    title=title,
                    description=description,
                    project_id=int(project_id),
                    assigned_to_id=int(assigned_to_id),
                    assigned_by_id=current_user.id,
                    deadline=datetime.strptime(deadline_str, "%Y-%m-%d").date(),
                    status="active",
                    attachment_path=attachment,
                )
                db.session.add(task)
                db.session.commit()
                flash("Task assigned across teams.", "success")
                return redirect(url_for("captain_dashboard"))

        elif action == "update_task_status":
            task_id = request.form.get("task_id")
            status = request.form.get("status")
            task = db.session.get(Task, int(task_id)) if task_id else None
            if not task or status not in TASK_STATUS_OPTIONS:
                flash("Invalid task or status.", "error")
            else:
                task.status = status
                db.session.commit()
                flash("Task status updated.", "success")
                return redirect(url_for("captain_dashboard", **request.args))

        elif action == "update_user":
            user_id = request.form.get("user_id")
            role = request.form.get("role")
            department = request.form.get("department")
            user = db.session.get(User, int(user_id)) if user_id else None
            if not user or role not in ROLE_OPTIONS or department not in DEPARTMENT_OPTIONS:
                flash("Invalid user settings.", "error")
            else:
                user.role = role
                user.department = department
                db.session.commit()
                flash("User role/department updated.", "success")
                return redirect(url_for("captain_dashboard"))

        elif action == "remove_user":
            user_id = request.form.get("user_id")
            user = db.session.get(User, int(user_id)) if user_id else None
            if not user or user.id == current_user.id:
                flash("Invalid user removal action.", "error")
            else:
                user.is_active = False
                db.session.commit()
                flash("User removed from team.", "success")
                return redirect(url_for("captain_dashboard"))

        elif action == "edit_report":
            report_id = request.form.get("report_id")
            text = request.form.get("text", "").strip()
            report = db.session.get(Report, int(report_id)) if report_id else None
            if not report or not text:
                flash("Invalid report edit.", "error")
            else:
                report.text = text
                db.session.commit()
                flash("Report updated.", "success")
                return redirect(url_for("captain_dashboard", **request.args))

        elif action == "delete_report":
            report_id = request.form.get("report_id")
            report = db.session.get(Report, int(report_id)) if report_id else None
            if not report:
                flash("Report not found.", "error")
            else:
                db.session.delete(report)
                db.session.commit()
                flash("Report deleted.", "success")
                return redirect(url_for("captain_dashboard", **request.args))

    # Task filters
    dept_filter = request.args.get("department", "all")
    proj_filter = request.args.get("project", "all")
    status_filter = request.args.get("status", "all")

    users = User.query.order_by(User.department.asc(), User.name.asc()).all()
    assignable_users = User.query.filter(User.is_active == True, User.role != "captain").order_by(User.name.asc()).all()
    authors = User.query.filter(User.is_active == True).order_by(User.name.asc()).all()
    projects = Project.query.order_by(Project.name.asc()).all()

    tasks_query = Task.query.join(User, Task.assigned_to_id == User.id)
    if dept_filter != "all":
        tasks_query = tasks_query.filter(User.department == dept_filter)
    if proj_filter != "all":
        tasks_query = tasks_query.filter(Task.project_id == int(proj_filter))
    if status_filter != "all":
        tasks_query = tasks_query.filter(Task.status == status_filter)
    tasks = tasks_query.order_by(Task.created_at.desc()).all()

    # Report filters
    report_type_filter = request.args.get("report_type", "all")
    report_department_filter = request.args.get("report_department", "all")
    report_project_filter = request.args.get("report_project", "all")
    report_author_filter = request.args.get("report_author", "all")

    reports_query = Report.query.join(User, Report.author_id == User.id)
    if report_type_filter != "all":
        reports_query = reports_query.filter(Report.report_type == report_type_filter)
    if report_department_filter != "all":
        reports_query = reports_query.filter(User.department == report_department_filter)
    if report_project_filter != "all":
        reports_query = reports_query.filter(Report.project_id == int(report_project_filter))
    if report_author_filter != "all":
        reports_query = reports_query.filter(Report.author_id == int(report_author_filter))
    reports = reports_query.order_by(Report.created_at.desc()).all()

    latest_notes = {}
    notes = DepartmentProgressNote.query.order_by(
        DepartmentProgressNote.week_start.desc(), DepartmentProgressNote.created_at.desc()
    ).all()
    for note in notes:
        key = (note.project_id, note.department)
        if key not in latest_notes:
            latest_notes[key] = note

    all_tasks = Task.query.order_by(Task.created_at.desc()).all()
    project_breakdown = []
    for project in projects:
        by_department = {}
        project_tasks = [t for t in all_tasks if t.project_id == project.id]
        for department in DEPARTMENT_OPTIONS:
            dept_tasks = [t for t in project_tasks if t.assignee.department == department and t.assignee.is_active]
            by_department[department] = {
                "tasks": dept_tasks,
                "note": latest_notes.get((project.id, department)),
            }
        project_breakdown.append((project, by_department))

    return render_template(
        "captain_dashboard.html",
        users=users,
        assignable_users=assignable_users,
        authors=authors,
        projects=projects,
        tasks=tasks,
        reports=reports,
        project_breakdown=project_breakdown,
        task_status_options=TASK_STATUS_OPTIONS,
        role_options=ROLE_OPTIONS,
        department_options=DEPARTMENT_OPTIONS,
        selected_filters={
            "department": dept_filter,
            "project": proj_filter,
            "status": status_filter,
            "report_type": report_type_filter,
            "report_department": report_department_filter,
            "report_project": report_project_filter,
            "report_author": report_author_filter,
        },
    )


@app.route("/files/<path:filename>")
@login_required
def files(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()

    projects = [
        Project(name="Mecanum", description="Drive base and SLAM-related work", status="active"),
        Project(name="Robotic Arm", description="Manipulator system development", status="active"),
        Project(name="Robotic Hand", description="End effector and precision grip development", status="active"),
        Project(name="Robotic Dog", description="Quadruped research platform", status="active"),
        Project(name="Corporate Operations", description="Sponsorship, outreach, documentation, and operations", status="active"),
    ]
    db.session.add_all(projects)
    db.session.flush()

    for project in projects:
        for department in DEPARTMENT_OPTIONS:
            db.session.add(ProjectDepartment(project_id=project.id, department=department))

    users = [
        ("Captain Jane", "captain@enro", "captain", "Corporate"),
        ("Mechanical Leader", "m.leader@enro", "leader", "Mechanical"),
        ("Electronics Leader", "e.leader@enro", "leader", "Electronics"),
        ("Software Leader", "s.leader@enro", "leader", "Software"),
        ("Corporate Leader", "c.leader@enro", "leader", "Corporate"),
    ]

    member_distribution = [
        ("Mechanical", "m", 7),
        ("Electronics", "e", 6),
        ("Software", "s", 6),
        ("Corporate", "c", 6),
    ]

    for department, prefix, count in member_distribution:
        for i in range(1, count + 1):
            users.append(
                (
                    f"{department} Member {i}",
                    f"{prefix}.member.{i}@enro",
                    "member",
                    department,
                )
            )

    for name, email, role, department in users:
        u = User(name=name, email=email, role=role, department=department, is_active=True)
        u.set_password("password123")
        db.session.add(u)

    db.session.commit()
    print("Database initialized with fresh seed data.")
    print("Users: 30 total (1 captain, 4 leaders, 25 members)")
    print("Projects: 5 total including Corporate Operations")
    print("No starter tasks or reports created.")
    print("Default password for all demo users: password123")


if __name__ == "__main__":
    app.run(debug=True)
