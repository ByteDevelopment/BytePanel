"""BytePanel — audit log helper.

Records events (logins, user/server management, file operations, limit
enforcement) into the JSON store. Safe to call from request contexts and
from background threads (watchdog), where ``current_user`` falls back to
"system".
"""

from .storage import db


def audit(action, message="", level="info", username=None, ip=None):
    if username is None:
        try:
            from flask_login import current_user

            if current_user.is_authenticated:
                username = current_user.username
        except Exception:
            pass
    if username is None:
        username = "system"

    if ip is None:
        try:
            from flask import request

            ip = request.remote_addr
        except Exception:
            pass

    try:
        db.add_log(level=level, action=action, message=message, username=username, ip=ip)
    except Exception:
        pass
