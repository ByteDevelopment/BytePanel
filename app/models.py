from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return datetime.utcnow()


class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin, created_at, theme="default"):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)
        self.created_at = created_at
        self.theme = theme

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def servers(self):
        from .storage import db

        return [s for s in db.all_servers() if s.owner_id == self.id]

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            username=data["username"],
            password_hash=data["password_hash"],
            is_admin=data.get("is_admin", False),
            created_at=_parse_dt(data.get("created_at")),
            theme=data.get("theme", "default"),
        )


class Server:
    def __init__(
        self,
        id,
        name,
        game,
        description,
        install_dir,
        start_command,
        port,
        status,
        pid,
        autostart,
        owner_id,
        created_at,
        memory_limit_mb=0,
        cpu_limit_pct=0,
        disk_limit_mb=0,
        template="custom",
    ):
        self.id = id
        self.name = name
        self.game = game
        self.description = description
        self.install_dir = install_dir
        self.start_command = start_command
        self.port = port
        self.status = status
        self.pid = pid
        self.autostart = autostart
        self.owner_id = owner_id
        self.created_at = created_at
        self.memory_limit_mb = int(memory_limit_mb or 0)
        self.cpu_limit_pct = int(cpu_limit_pct or 0)
        self.disk_limit_mb = int(disk_limit_mb or 0)
        self.template = template or "custom"

    @property
    def has_limits(self):
        return bool(self.memory_limit_mb or self.cpu_limit_pct or self.disk_limit_mb)

    @property
    def owner(self):
        from .storage import db

        return db.get_user(self.owner_id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "game": self.game,
            "description": self.description,
            "install_dir": self.install_dir,
            "start_command": self.start_command,
            "port": self.port,
            "status": self.status,
            "pid": self.pid,
            "autostart": self.autostart,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_limit_pct": self.cpu_limit_pct,
            "disk_limit_mb": self.disk_limit_mb,
            "template": self.template,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            name=data["name"],
            game=data.get("game", "Custom"),
            description=data.get("description", ""),
            install_dir=data["install_dir"],
            start_command=data["start_command"],
            port=data["port"],
            status=data.get("status", "offline"),
            pid=data.get("pid", 0),
            autostart=data.get("autostart", False),
            owner_id=data["owner_id"],
            created_at=_parse_dt(data.get("created_at")),
            memory_limit_mb=data.get("memory_limit_mb", 0),
            cpu_limit_pct=data.get("cpu_limit_pct", 0),
            disk_limit_mb=data.get("disk_limit_mb", 0),
            template=data.get("template", "custom"),
        )

    def __repr__(self):
        return f"<Server {self.id}:{self.name}>"
