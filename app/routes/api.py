"""BytePanel — remote admin API.

URL-style API authenticated with the admin account's password as the key.

Examples:
    /api/admin/<admin_password>/adduser/Annie/Annieishere
    /api/admin/<admin_password>/addserver/MyServer/25565?game=Minecraft&start_command=python.exe%20main.py
"""

import os

from flask import Blueprint, jsonify, request

from ..audit import audit
from ..config import SERVERS_DIR
from ..server_templates import get_template
from ..storage import db
from .helpers import slugify

api_bp = Blueprint("api", __name__)


def _authenticate(key):
    """Return the admin whose password matches ``key``, else None."""
    if not key:
        return None
    for user in db.all_users():
        if user.is_admin and user.password_hash and user.check_password(key):
            return user
    return None


def _as_bool(value):
    return str(value).lower() in ("1", "true", "yes", "on")


def _as_int(value, default=0):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _template_for_game(game):
    game_lower = (game or "").lower()
    if "minecraft" in game_lower:
        return "minecraft"
    if "python" in game_lower:
        return "python"
    return "custom"


@api_bp.route(
    "/api/admin/<key>/adduser/<username>/<password>",
    methods=["GET", "POST"],
)
def add_user(key, username, password):
    admin = _authenticate(key)
    if admin is None:
        return jsonify({"ok": False, "error": "Invalid admin key"}), 401

    username = username.strip()
    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password are required"}), 400
    if db.get_user_by_username(username):
        return jsonify({"ok": False, "error": "Username is already taken"}), 409

    body = request.json if request.is_json else {}
    is_admin = _as_bool(
        request.args.get("admin", body.get("admin") if isinstance(body, dict) else None)
    )
    user = db.add_user(username=username, password_hash="", is_admin=is_admin)
    user.set_password(password)
    db.save_user(user)
    audit(
        "user.create",
        f'user "{username}" created via API by "{admin.username}"'
        + (" (admin)" if is_admin else ""),
        username=admin.username,
    )
    return jsonify(
        {
            "ok": True,
            "endpoint": "adduser",
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
        }
    )


@api_bp.route(
    "/api/admin/<key>/addserver/<name>/<int:port>",
    methods=["GET", "POST"],
)
def add_server(key, name, port):
    admin = _authenticate(key)
    if admin is None:
        return jsonify({"ok": False, "error": "Invalid admin key"}), 401

    name = name.strip()
    if not name:
        return jsonify({"ok": False, "error": "Name is required"}), 400
    if not (1 <= port <= 65535):
        return jsonify({"ok": False, "error": "Port must be between 1 and 65535"}), 400
    if any(s.port == port for s in db.all_servers()):
        return jsonify({"ok": False, "error": "Port is already assigned"}), 409

    d = request.json if (request.is_json and request.method == "POST") else request.args

    owner_name = (d.get("owner") or "").strip()
    owner = db.get_user_by_username(owner_name) if owner_name else None
    if owner is None:
        owner = _authenticate(key)

    start_command = (d.get("start_command") or "").strip()
    template_key = (d.get("template") or "custom").strip() or "custom"
    tpl = get_template(template_key)
    if not start_command and tpl["command"]:
        start_command = tpl["command"]
    if not start_command and tpl["game"]:
        d_game = (d.get("game") or "").strip()
        if not d_game or d_game.lower() == "custom":
            d["game"] = tpl["game"]
    game = (d.get("game") or "Custom").strip()

    dir_name = (d.get("dir_name") or "").strip() or slugify(name)
    install_dir = os.path.join(SERVERS_DIR, slugify(dir_name))
    if not _as_bool(d.get("create_dir", "1")):
        pass
    else:
        os.makedirs(install_dir, exist_ok=True)

    server = db.add_server(
        name=name,
        game=game,
        description=(d.get("description") or "").strip(),
        install_dir=install_dir,
        start_command=start_command,
        port=port,
        owner_id=owner.id,
        autostart=_as_bool(d.get("autostart")),
        memory_limit_mb=_as_int(d.get("memory_limit_mb")),
        cpu_limit_pct=_as_int(d.get("cpu_limit_pct")),
        disk_limit_mb=_as_int(d.get("disk_limit_mb")),
        template=template_key,
    )
    audit(
        "server.create",
        f'server "{name}" created via API on port {port}',
        username=admin.username,
    )
    return (
        jsonify(
            {
                "ok": True,
                "endpoint": "addserver",
                "id": server.id,
                "name": server.name,
                "port": server.port,
                "install_dir": server.install_dir,
                "start_command": server.start_command,
                "owner": owner.username,
            }
        ),
        201,
    )


@api_bp.route("/api/admin/<key>/status/<int:server_id>", methods=["GET"])
def server_status(key, server_id):
    if _authenticate(key) is None:
        return jsonify({"ok": False, "error": "Invalid admin key"}), 401
    server = db.get_server(server_id)
    if server is None:
        return jsonify({"ok": False, "error": "Server not found"}), 404
    from .. import server_manager

    return jsonify(
        {
            "ok": True,
            "id": server.id,
            "name": server.name,
            "status": server_manager.status(server),
        }
    )
