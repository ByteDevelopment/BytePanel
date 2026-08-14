import os
import re

from flask import abort
from flask_login import current_user, login_required
from functools import wraps

from ..storage import db


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def get_server_or_404(server_id):
    server = db.get_server(server_id)
    if server is None:
        abort(404)
    if not current_user.is_admin and server.owner_id != current_user.id:
        abort(403)
    return server


def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9\-_ ]", "", text).strip().lower()
    text = re.sub(r"[ ]+", "-", text)
    return text or "server"


def safe_join(base_dir, rel_path):
    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, rel_path or ""))
    if target != base and not target.startswith(base + os.sep):
        abort(403)
    return target
