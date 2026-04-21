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
    role = db.Column(db.String(20), nullable=False)  # member | leader | captain
    department = db.Column(db.String(50), nullable=False)

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
    status = db.Column(db.String(20), nullable=False, default="todo")
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    reports = db.relationship("Report", backref="related_task")


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    related_task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)
    report_type = db.Column(db.String(20), nullable=False)  # member | leader
    text = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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


def current_week_start() -> datetime:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return datetime.combine(monday, datetime.min.time())


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
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "error")

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
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        task_id = request.form.get("task_id") or None
        if not text:
            flash("Report text is required.", "error")
        else:
            attachment = save_upload(request.files.get("attachment"))
            report = Report(
                author_id=current_user.id,
                related_task_id=int(task_id) if task_id else None,
                report_type="member",
                text=text,
                attachment_path=attachment,
            )
            db.session.add(report)
            db.session.commit()
            flash("Weekly report submitted.", "success")
            return redirect(url_for("member_dashboard"))

    tasks = (
        Task.query.filter_by(assigned_to_id=current_user.id)
        .order_by(Task.deadline.asc(), Task.created_at.desc())
        .all()
    )
    reports = Report.query.filter_by(author_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("member_dashboard.html", tasks=tasks, reports=reports)


@app.route("/leader", methods=["GET", "POST"])
@login_required
@role_required("leader")
def leader_dashboard():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_task":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            project_id = request.form.get("project_id")
            deadline_str = request.form.get("deadline")
            assigned_to_id = request.form.get("assigned_to_id")
            if not all([title, description, project_id, deadline_str, assigned_to_id]):
                flash("Please fill all task fields.", "error")
            else:
                member = db.session.get(User, int(assigned_to_id))
                if not member or member.department != current_user.department:
                    flash("You can assign tasks only to your own department members.", "error")
                else:
                    attachment = save_upload(request.files.get("task_attachment"))
                    task = Task(
                        title=title,
                        description=description,
                        project_id=int(project_id),
                        assigned_to_id=member.id,
                        assigned_by_id=current_user.id,
                        deadline=datetime.strptime(deadline_str, "%Y-%m-%d").date(),
                        status="todo",
                        attachment_path=attachment,
                    )
                    db.session.add(task)
                    db.session.commit()
                    flash("Task assigned.", "success")
                    return redirect(url_for("leader_dashboard"))

        if action == "submit_report":
            text = request.form.get("text", "").strip()
            if not text:
                flash("Leader report text is required.", "error")
            else:
                attachment = save_upload(request.files.get("leader_attachment"))
                report = Report(
                    author_id=current_user.id,
                    report_type="leader",
                    text=text,
                    attachment_path=attachment,
                )
                db.session.add(report)
                db.session.commit()
                flash("Leader weekly report submitted.", "success")
                return redirect(url_for("leader_dashboard"))

    members = User.query.filter_by(role="member", department=current_user.department).order_by(User.name.asc()).all()
    member_ids = [m.id for m in members]

    member_tasks = (
        Task.query.filter(Task.assigned_to_id.in_(member_ids) if member_ids else False)
        .order_by(Task.deadline.asc())
        .all()
    )
    tasks_by_member = {}
    for t in member_tasks:
        tasks_by_member.setdefault(t.assigned_to_id, []).append(t)

    week_start = current_week_start()
    recent_reports = (
        Report.query.filter(Report.author_id.in_(member_ids) if member_ids else False)
        .filter(Report.report_type == "member")
        .filter(Report.created_at >= week_start)
        .all()
    )
    submitted_member_ids = {r.author_id for r in recent_reports}
    missing_reports = [m for m in members if m.id not in submitted_member_ids]

    projects = Project.query.order_by(Project.name.asc()).all()
    leader_reports = (
        Report.query.filter_by(author_id=current_user.id, report_type="leader")
        .order_by(Report.created_at.desc())
        .all()
    )

    return render_template(
        "leader_dashboard.html",
        members=members,
        tasks_by_member=tasks_by_member,
        projects=projects,
        missing_reports=missing_reports,
        leader_reports=leader_reports,
        week_start=week_start,
    )


@app.route("/captain", methods=["GET", "POST"])
@login_required
@role_required("captain")
def captain_dashboard():
    if request.method == "POST":
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
                status="todo",
                attachment_path=attachment,
            )
            db.session.add(task)
            db.session.commit()
            flash("Task assigned across teams.", "success")
            return redirect(url_for("captain_dashboard"))

    users = User.query.order_by(User.department.asc(), User.name.asc()).all()
    projects = Project.query.order_by(Project.name.asc()).all()
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    reports = Report.query.order_by(Report.created_at.desc()).all()

    project_breakdown = []
    for project in projects:
        p_tasks = [t for t in tasks if t.project_id == project.id]
        by_department = {}
        for task in p_tasks:
            dept = task.assignee.department
            by_department.setdefault(dept, []).append(task)
        project_breakdown.append((project, by_department))

    return render_template(
        "captain_dashboard.html",
        users=users,
        projects=projects,
        tasks=tasks,
        reports=reports,
        project_breakdown=project_breakdown,
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
    ]
    db.session.add_all(projects)
    db.session.flush()

    project_department_map = {
        "Mecanum": ["Mechanical", "Electronics", "Software"],
        "Robotic Arm": ["Mechanical", "Electronics", "Software"],
        "Robotic Hand": ["Mechanical", "Electronics"],
        "Robotic Dog": ["Mechanical", "Electronics", "Software", "Corporate"],
    }
    for project in projects:
        for department in project_department_map[project.name]:
            db.session.add(ProjectDepartment(project_id=project.id, department=department))

    users = [
        ("Captain Jane", "captain@robotics.local", "captain", "Corporate"),
        ("Mina Mechanical", "leader.mech@robotics.local", "leader", "Mechanical"),
        ("Eli Electronics", "leader.elec@robotics.local", "leader", "Electronics"),
        ("Sam Software", "leader.soft@robotics.local", "leader", "Software"),
        ("Moe Member", "member.mech@robotics.local", "member", "Mechanical"),
        ("Nora Member", "member.elec@robotics.local", "member", "Electronics"),
        ("Ivy Member", "member.soft@robotics.local", "member", "Software"),
        ("Cora Member", "member.corp@robotics.local", "member", "Corporate"),
    ]

    created_users = []
    for name, email, role, department in users:
        u = User(name=name, email=email, role=role, department=department)
        u.set_password("password123")
        db.session.add(u)
        created_users.append(u)

    db.session.flush()

    captain = next(u for u in created_users if u.role == "captain")
    member_mech = next(u for u in created_users if u.email == "member.mech@robotics.local")

    starter_task = Task(
        title="SLAM Integration Baseline",
        description="Create the baseline SLAM module integration with drive stack.",
        project_id=projects[0].id,
        assigned_to_id=member_mech.id,
        assigned_by_id=captain.id,
        deadline=date.today() + timedelta(days=7),
        status="in_progress",
    )
    db.session.add(starter_task)

    db.session.commit()
    print("Database initialized with sample data.")
    print("Default password for all demo users: password123")


if __name__ == "__main__":
    app.run(debug=True)
