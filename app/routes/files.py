import os
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..audit import audit
from .helpers import get_server_or_404, safe_join

files_bp = Blueprint("files", __name__)


@files_bp.route("/servers/<int:server_id>/files")
@login_required
def index(server_id):
    server = get_server_or_404(server_id)
    rel = request.args.get("path", "").replace("\\", "/").lstrip("/")
    target = safe_join(server.install_dir, rel)

    if not os.path.isdir(target):
        flash("Directory not found.", "error")
        return redirect(url_for("files.index", server_id=server.id))

    items = []
    for entry in sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name.lower())):
        try:
            stat = entry.stat()
            items.append(
                {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                }
            )
        except OSError:
            continue

    parent = "/".join(rel.split("/")[:-1]) if rel else ""
    return render_template(
        "files.html",
        server=server,
        items=items,
        rel=rel,
        parent=parent,
        rel_display="/" + rel if rel else "/",
    )


@files_bp.route("/servers/<int:server_id>/files/edit")
@login_required
def edit(server_id):
    server = get_server_or_404(server_id)
    rel = request.args.get("path", "").replace("\\", "/").lstrip("/")
    target = safe_join(server.install_dir, rel)

    if not os.path.isfile(target):
        flash("File not found.", "error")
        return redirect(url_for("files.index", server_id=server.id))

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        flash(f"Could not read file: {exc}", "error")
        return redirect(url_for("files.index", server_id=server.id))

    return render_template(
        "file_edit.html",
        server=server,
        rel=rel,
        file_name=os.path.basename(target),
        content=content,
    )


@files_bp.route("/servers/<int:server_id>/files/save", methods=["POST"])
@login_required
def save(server_id):
    server = get_server_or_404(server_id)
    rel = request.form.get("path", "").replace("\\", "/").lstrip("/")
    target = safe_join(server.install_dir, rel)

    if not os.path.isfile(target):
        flash("File not found.", "error")
        return redirect(url_for("files.index", server_id=server.id))

    try:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(request.form.get("content", ""))
        flash("File saved.", "success")
        audit("file.edit", f'"{rel}" saved on "{server.name}"')
    except OSError as exc:
        flash(f"Could not save file: {exc}", "error")

    return redirect(url_for("files.index", server_id=server.id, path=os.path.dirname(rel)))


@files_bp.route("/servers/<int:server_id>/files/upload", methods=["POST"])
@login_required
def upload(server_id):
    server = get_server_or_404(server_id)
    rel = request.form.get("path", "").replace("\\", "/").lstrip("/")
    target = safe_join(server.install_dir, rel)

    files = request.files.getlist("files")
    if not files or not files[0].filename:
        flash("No files selected.", "error")
        return redirect(url_for("files.index", server_id=server.id, path=rel))

    saved = 0
    for f in files:
        if not f.filename:
            continue
        dest = safe_join(target, os.path.basename(f.filename))
        try:
            f.save(dest)
            saved += 1
        except OSError as exc:
            flash(f"Failed to save {f.filename}: {exc}", "error")

    flash(f"Uploaded {saved} file(s).", "success")
    if saved:
        audit("file.upload", f"{saved} file(s) uploaded to \"{server.name}\"")
    return redirect(url_for("files.index", server_id=server.id, path=rel))


@files_bp.route("/servers/<int:server_id>/files/new", methods=["POST"])
@login_required
def create(server_id):
    server = get_server_or_404(server_id)
    rel = request.form.get("path", "").replace("\\", "/").lstrip("/")
    target = safe_join(server.install_dir, rel)
    kind = request.form.get("kind", "file")
    name = request.form.get("name", "").strip()

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("files.index", server_id=server.id, path=rel))

    dest = safe_join(target, name)
    try:
        if kind == "dir":
            os.makedirs(dest, exist_ok=False)
        else:
            if os.path.isdir(dest):
                raise OSError("A directory with that name already exists.")
            with open(dest, "w", encoding="utf-8") as f:
                f.write("")
        flash(f'Created "{name}".', "success")
        audit("file.create", f'"{name}" created on "{server.name}"')
    except OSError as exc:
        flash(f"Could not create: {exc}", "error")

    return redirect(url_for("files.index", server_id=server.id, path=rel))


@files_bp.route("/servers/<int:server_id>/files/rename", methods=["POST"])
@login_required
def rename(server_id):
    server = get_server_or_404(server_id)
    rel = request.form.get("path", "").replace("\\", "/").lstrip("/")
    new_name = request.form.get("new_name", "").strip()
    parent = os.path.dirname(rel)
    target = safe_join(server.install_dir, rel)

    if not new_name:
        flash("New name is required.", "error")
        return redirect(url_for("files.index", server_id=server.id, path=parent))

    new_path = safe_join(server.install_dir, os.path.join(parent, new_name))
    try:
        os.rename(target, new_path)
        flash(f'Renamed to "{new_name}".', "success")
        audit("file.rename", f'"{rel}" renamed to "{new_name}" on "{server.name}"')
    except OSError as exc:
        flash(f"Could not rename: {exc}", "error")

    return redirect(url_for("files.index", server_id=server.id, path=parent))


@files_bp.route("/servers/<int:server_id>/files/delete", methods=["POST"])
@login_required
def delete(server_id):
    server = get_server_or_404(server_id)
    rel = request.form.get("path", "").replace("\\", "/").lstrip("/")
    parent = os.path.dirname(rel)
    target = safe_join(server.install_dir, rel)

    if os.path.abspath(target) == os.path.abspath(server.install_dir):
        flash("You cannot delete the server root.", "error")
        return redirect(url_for("files.index", server_id=server.id))

    try:
        if os.path.isdir(target):
            import shutil

            shutil.rmtree(target)
        else:
            os.remove(target)
        flash(f'Deleted "{os.path.basename(target)}".', "success")
        audit("file.delete", f'"{rel}" deleted from "{server.name}"', level="warn")
    except OSError as exc:
        flash(f"Could not delete: {exc}", "error")

    return redirect(url_for("files.index", server_id=server.id, path=parent))
