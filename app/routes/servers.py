from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import server_manager
from ..audit import audit
from ..server_templates import get_template, resolve_command
from ..storage import db
from .helpers import get_server_or_404

servers_bp = Blueprint("servers", __name__)


@servers_bp.route("/servers/<int:server_id>")
@login_required
def detail(server_id):
    server = get_server_or_404(server_id)
    server.status = server_manager.status(server)
    from ..server_templates import resolve_command as _resolve
    resolved = _resolve(server)
    return render_template("server_detail.html", server=server, resolved_command=resolved)


@servers_bp.route("/servers/<int:server_id>/console")
@login_required
def console(server_id):
    server = get_server_or_404(server_id)
    server.status = server_manager.status(server)
    return render_template("console.html", server=server)


@servers_bp.route("/servers/<int:server_id>/settings")
@login_required
def settings(server_id):
    server = get_server_or_404(server_id)
    server.status = server_manager.status(server)
    template = get_template(server.template)
    resolved = resolve_command(server)
    return render_template(
        "settings.html",
        server=server,
        template=template,
        resolved_command=resolved,
    )


@servers_bp.route("/servers/<int:server_id>/kill", methods=["POST"])
@login_required
def kill(server_id):
    server = get_server_or_404(server_id)
    server_manager.kill(server)
    audit("server.kill", f'server "{server.name}" force-killed', level="warn")
    return redirect(request.referrer or url_for("servers.detail", server_id=server.id))


@servers_bp.route("/servers/<int:server_id>/start", methods=["POST"])
@login_required
def start(server_id):
    server = get_server_or_404(server_id)
    try:
        server_manager.start(server)
        audit("server.start", f'server "{server.name}" started')
    except Exception as exc:
        audit(
            "server.start",
            f'server "{server.name}" failed to start: {exc}',
            level="error",
        )
    return redirect(request.referrer or url_for("servers.detail", server_id=server.id))


@servers_bp.route("/servers/<int:server_id>/stop", methods=["POST"])
@login_required
def stop(server_id):
    server = get_server_or_404(server_id)
    server_manager.stop(server)
    audit("server.stop", f'server "{server.name}" stopped')
    return redirect(request.referrer or url_for("servers.detail", server_id=server.id))


@servers_bp.route("/servers/<int:server_id>/restart", methods=["POST"])
@login_required
def restart(server_id):
    server = get_server_or_404(server_id)
    server_manager.restart(server)
    audit("server.restart", f'server "{server.name}" restarted')
    return redirect(request.referrer or url_for("servers.detail", server_id=server.id))


@servers_bp.route("/servers/<int:server_id>/startup", methods=["POST"])
@login_required
def startup(server_id):
    server = get_server_or_404(server_id)
    command = request.form.get("start_command", "").strip()
    if not command:
        pass
    else:
        server.start_command = command
        db.save_server(server)
        audit("server.edit", f'startup command for "{server.name}" changed')
    return redirect(request.referrer or url_for("servers.detail", server_id=server.id))


@servers_bp.route("/servers/<int:server_id>/api/status")
@login_required
def api_status(server_id):
    server = get_server_or_404(server_id)
    return jsonify({"status": server_manager.status(server)})


@servers_bp.route("/servers/<int:server_id>/api/stats")
@login_required
def api_stats(server_id):
    server = get_server_or_404(server_id)
    return jsonify(server_manager.get_stats(server))


@servers_bp.route("/servers/<int:server_id>/api/logs")
@login_required
def api_logs(server_id):
    server = get_server_or_404(server_id)
    after = request.args.get("after", 0, type=int)
    sp = server_manager.get(server.id)
    lines = sp.logs_since(after) if sp else []
    last = lines[-1][0] if lines else after
    return jsonify(
        {
            "status": server_manager.status(server),
            "last": last,
            "logs": [{"id": i, "text": t} for i, t in lines],
        }
    )


@servers_bp.route("/servers/<int:server_id>/api/command", methods=["POST"])
@login_required
def api_command(server_id):
    server = get_server_or_404(server_id)
    command = (request.json or {}).get("command", "").strip()
    sp = server_manager.get(server.id)
    ok = sp.send_command(command) if sp else False
    audit("server.command", f'command sent to "{server.name}": {command}')
    return jsonify({"ok": ok})
