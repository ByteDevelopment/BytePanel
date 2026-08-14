import os
import shutil
import subprocess
import sys

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import server_manager
from ..audit import audit
from ..config import SERVERS_DIR
from ..storage import db
from ..server_templates import get_template, list_templates
from .helpers import admin_required, slugify

admin_bp = Blueprint("admin", __name__)


def _sync_statuses(servers):
    for server in servers:
        server.status = server_manager.status(server)
    return servers


@admin_bp.route("/admin")
@admin_required
def dashboard():
    servers = _sync_statuses(sorted(db.all_servers(), key=lambda s: s.name.lower()))
    users = sorted(db.all_users(), key=lambda u: u.username.lower())
    running = sum(1 for s in servers if s.status == "running")
    return render_template(
        "admin/dashboard.html",
        servers=servers,
        users=users,
        running=running,
        total=len(servers),
    )


@admin_bp.route("/admin/servers")
@admin_required
def servers():
    servers = _sync_statuses(sorted(db.all_servers(), key=lambda s: s.name.lower()))
    return render_template("admin/servers.html", servers=servers)


def _parse_limit(raw):
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 0


def _form_data():
    d = {
        "name": request.form.get("name", "").strip(),
        "game": request.form.get("game", "").strip() or "Custom",
        "description": request.form.get("description", "").strip(),
        "port": request.form.get("port", "").strip(),
        "start_command": request.form.get("start_command", "").strip(),
        "owner_id": request.form.get("owner_id", "").strip(),
        "create_dir": request.form.get("create_dir") == "on",
        "create_pyenv": request.form.get("create_pyenv") == "on",
        "autostart": request.form.get("autostart") == "on",
        "template": request.form.get("template", "").strip() or "custom",
        "memory_limit_mb": _parse_limit(request.form.get("memory_limit_mb")),
        "cpu_limit_pct": _parse_limit(request.form.get("cpu_limit_pct")),
        "disk_limit_mb": _parse_limit(request.form.get("disk_limit_mb")),
    }
    template = get_template(d["template"])
    if not d["start_command"] and template["command"]:
        d["start_command"] = template["command"]
    if (not d["game"] or d["game"] == "Custom") and template["game"]:
        d["game"] = template["game"]
    return d


def _template_for_game(game):
    game_lower = (game or "").lower()
    if "minecraft" in game_lower:
        return "minecraft"
    if "python" in game_lower:
        return "python"
    return "custom"


def _default_python_command():
    if os.name == "nt":
        return "venv\\Scripts\\python.exe main.py"
    return "venv/bin/python main.py"


def _create_python_env(install_dir):
    venv_path = os.path.join(install_dir, "venv")
    if os.path.isdir(venv_path):
        return venv_path
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    return venv_path


def _port_taken(port, exclude_id=None):
    for s in db.all_servers():
        if s.port == port and s.id != exclude_id:
            return True
    return False


@admin_bp.route("/admin/servers/new", methods=["GET", "POST"])
@admin_required
def new_server():
    users = sorted(db.all_users(), key=lambda u: u.username.lower())

    if request.method == "POST":
        d = _form_data()
        error = None
        if not d["name"]:
            error = "Name is required."
        elif not d["port"] or not d["port"].isdigit() or not (1 <= int(d["port"]) <= 65535):
            error = "Port must be a number between 1 and 65535."
        elif _port_taken(int(d["port"])):
            error = "That port is already assigned to another server."
        elif not d["start_command"] and not d["create_pyenv"]:
            error = "Start command is required."
        elif not d["owner_id"] or not d["owner_id"].isdigit():
            error = "Please choose an owner."
        else:
            owner = db.get_user(int(d["owner_id"]))
            if owner is None:
                error = "Please choose a valid owner."
            else:
                dir_name = request.form.get("dir_name", "").strip() or slugify(d["name"])
                install_dir = os.path.join(SERVERS_DIR, slugify(dir_name))
                if d["create_dir"] and not os.path.isdir(install_dir):
                    os.makedirs(install_dir, exist_ok=True)

                start_command = d["start_command"]
                try:
                    if d["create_pyenv"]:
                        _create_python_env(install_dir)
                        if not start_command:
                            start_command = _default_python_command()
                except Exception as exc:
                    flash(f"Could not create Python venv: {exc}", "error")
                    return render_template(
                        "admin/server_form.html",
                        users=users,
                        server=None,
                        templates=list_templates(),
                    )

                db.add_server(
                    name=d["name"],
                    game=d["game"],
                    description=d["description"],
                    install_dir=install_dir,
                    start_command=start_command,
                    port=int(d["port"]),
                    owner_id=owner.id,
                    autostart=d["autostart"],
                    memory_limit_mb=d["memory_limit_mb"],
                    cpu_limit_pct=d["cpu_limit_pct"],
                    disk_limit_mb=d["disk_limit_mb"],
                    template=d["template"],
                )
                flash(f'Server "{d["name"]}" created.', "success")
                audit(
                    "server.create",
                    f'server "{d["name"]}" created on port {d["port"]}'
                    f' (template: {d["template"]})',
                )
                return redirect(url_for("admin.servers"))

        if error:
            flash(error, "error")

    return render_template(
        "admin/server_form.html", users=users, server=None, templates=list_templates()
    )


@admin_bp.route("/admin/servers/<int:server_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_server(server_id):
    server = db.get_server(server_id)
    if server is None:
        flash("Server not found.", "error")
        return redirect(url_for("admin.servers"))
    users = sorted(db.all_users(), key=lambda u: u.username.lower())

    if request.method == "POST":
        d = _form_data()
        error = None
        if not d["name"]:
            error = "Name is required."
        elif not d["port"] or not d["port"].isdigit() or not (1 <= int(d["port"]) <= 65535):
            error = "Port must be a number between 1 and 65535."
        elif _port_taken(int(d["port"]), exclude_id=server.id):
            error = "That port is already assigned to another server."
        elif not d["start_command"]:
            error = "Start command is required."
        elif not d["owner_id"] or not d["owner_id"].isdigit():
            error = "Please choose an owner."
        else:
            owner = db.get_user(int(d["owner_id"]))
            if owner is None:
                error = "Please choose a valid owner."
            else:
                server.name = d["name"]
                server.game = d["game"]
                server.description = d["description"]
                server.start_command = d["start_command"]
                server.port = int(d["port"])
                server.autostart = d["autostart"]
                server.owner_id = owner.id
                server.memory_limit_mb = d["memory_limit_mb"]
                server.cpu_limit_pct = d["cpu_limit_pct"]
                server.disk_limit_mb = d["disk_limit_mb"]
                server.template = d["template"]
                db.save_server(server)
                flash(f'Server "{server.name}" updated.', "success")
                audit(
                    "server.edit",
                    f'server "{server.name}" settings updated'
                    f' (template: {d["template"]})',
                )
                return redirect(url_for("admin.servers"))

        if error:
            flash(error, "error")

    return render_template("admin/server_form.html", users=users, server=server, templates=list_templates())


@admin_bp.route("/admin/servers/<int:server_id>/delete", methods=["POST"])
@admin_required
def delete_server(server_id):
    server = db.get_server(server_id)
    if server is None:
        flash("Server not found.", "error")
        return redirect(url_for("admin.servers"))

    if server_manager.status(server) == "running":
        server_manager.stop(server)

    name = server.name
    install_dir = server.install_dir
    delete_files = request.form.get("delete_files") == "on"
    db.delete_server(server.id)

    if delete_files and os.path.isdir(install_dir):
        shutil.rmtree(install_dir, ignore_errors=True)

    audit(
        "server.delete",
        f'server "{name}" deleted'
        + (" with files" if delete_files else ""),
        level="warn",
    )
    flash(f'Server "{name}" deleted.', "success")
    return redirect(url_for("admin.servers"))


@admin_bp.route("/admin/logs")
@admin_required
def logs():
    query = request.args.get("q", "").strip().lower()
    level = request.args.get("level", "").strip().lower()
    entries = db.all_logs(limit=1000)
    if query:
        entries = [
            e
            for e in entries
            if query in e.get("username", "").lower()
            or query in e.get("action", "").lower()
            or query in e.get("message", "").lower()
            or query in e.get("ip", "") or ""
        ]
    if level:
        entries = [e for e in entries if e.get("level") == level]
    return render_template(
        "admin/logs.html",
        entries=entries,
        total=db.count_logs(),
        query=request.args.get("q", ""),
        level=level,
    )


@admin_bp.route("/admin/logs/clear", methods=["POST"])
@admin_required
def clear_logs():
    count = db.count_logs()
    db.clear_logs()
    audit("logs.clear", f"audit log cleared ({count} entries removed)", level="warn")
    flash("Audit log cleared.", "success")
    return redirect(url_for("admin.logs"))


@admin_bp.route("/admin/users")
@admin_required
def users():
    users = sorted(db.all_users(), key=lambda u: u.username.lower())
    return render_template("admin/users.html", users=users)


@admin_bp.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        is_admin = request.form.get("is_admin") == "on"

        if not username or not password:
            flash("Username and password are required.", "error")
        elif db.get_user_by_username(username):
            flash("That username is already taken.", "error")
        else:
            user = db.add_user(username=username, password_hash="", is_admin=is_admin)
            user.set_password(password)
            db.save_user(user)
            audit(
                "user.create",
                f'user "{username}" created'
                + (" (admin)" if is_admin else ""),
            )
            flash(f'User "{username}" created.', "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=None)


@admin_bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.get_user(user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        is_admin = request.form.get("is_admin") == "on"

        existing = db.get_user_by_username(username)
        if not username:
            flash("Username is required.", "error")
        elif existing and existing.id != user.id:
            flash("That username is already taken.", "error")
        else:
            user.username = username
            user.is_admin = is_admin
            if password:
                user.set_password(password)
            db.save_user(user)
            audit("user.edit", f'user "{username}" updated')
            flash(f'User "{username}" updated.', "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=user)


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.get_user(user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))

    name = user.username
    for server in db.servers_for(user.id):
        db.delete_server(server.id)
    db.delete_user(user.id)
    audit("user.delete", f'user "{name}" deleted', level="warn")
    flash(f'User "{name}" deleted.', "success")
    return redirect(url_for("admin.users"))
