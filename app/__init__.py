import os

from flask import Flask, request
from flask_login import LoginManager

from .config import INSTANCE_DIR, SECRET_FILE, SERVERS_DIR
from .models import User
from .storage import db

login_manager = LoginManager()
server_manager = None


def _load_secret():
    if not os.path.exists(SECRET_FILE):
        os.makedirs(INSTANCE_DIR, exist_ok=True)
        with open(SECRET_FILE, "w") as f:
            f.write(os.urandom(48).hex())
    with open(SECRET_FILE) as f:
        return f.read().strip()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = _load_secret()

    os.makedirs(INSTANCE_DIR, exist_ok=True)
    os.makedirs(SERVERS_DIR, exist_ok=True)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."

    global server_manager
    from .server_manager import ServerManager

    server_manager = ServerManager(app)

    from .routes.admin import admin_bp
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.files import files_bp
    from .routes.main import main_bp
    from .routes.servers import servers_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(files_bp)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.get_user(int(user_id))
        except (TypeError, ValueError):
            return None

    @app.context_processor
    def inject_globals():
        ep = request.endpoint or ""
        if ep == "main.dashboard":
            active = "dashboard"
        elif ep == "admin.dashboard":
            active = "admin"
        elif ep.startswith("admin.") and "user" in ep:
            active = "admin-users"
        elif ep.startswith("admin.") and "log" in ep:
            active = "admin-logs"
        elif ep.startswith("admin."):
            active = "admin-servers"
        else:
            active = ""
        return {"panel_version": "1.0.0", "active_page": active}

    server_manager.autostart()

    return app
