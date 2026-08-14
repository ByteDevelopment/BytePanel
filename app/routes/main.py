from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from .. import server_manager
from ..storage import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    servers = sorted(db.servers_for(current_user.id), key=lambda s: s.name.lower())
    for server in servers:
        server.status = server_manager.status(server)

    return render_template("dashboard.html", servers=servers)
