import json
import os
import threading
from datetime import datetime

from .config import DATA_FILE
from .models import Server, User

MAX_AUDIT_LOGS = 1000


class Database:
    """Simple JSON-file backed store for users and servers."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.RLock()
        self._data = self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = {}
        else:
            data = {}
        data.setdefault("users", [])
        data.setdefault("servers", [])
        data.setdefault("logs", [])
        data.setdefault("_next", {"user": 1, "server": 1, "log": 1})
        return data

    def _save(self):
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)


    def add_user(self, username, password_hash, is_admin=False):
        with self._lock:
            user = User(
                id=self._data["_next"]["user"],
                username=username,
                password_hash=password_hash,
                is_admin=is_admin,
                created_at=datetime.utcnow(),
                theme="default",
            )
            self._data["_next"]["user"] += 1
            self._data["users"].append(user.to_dict())
            self._save()
            return user

    def get_user(self, user_id):
        for row in self._data["users"]:
            if row["id"] == user_id:
                return User.from_dict(row)
        return None

    def get_user_by_username(self, username):
        for row in self._data["users"]:
            if row["username"] == username:
                return User.from_dict(row)
        return None

    def all_users(self):
        return [User.from_dict(r) for r in self._data["users"]]

    def count_users(self):
        return len(self._data["users"])

    def save_user(self, user):
        with self._lock:
            for i, row in enumerate(self._data["users"]):
                if row["id"] == user.id:
                    self._data["users"][i] = user.to_dict()
                    break
            self._save()

    def delete_user(self, user_id):
        with self._lock:
            self._data["users"] = [
                r for r in self._data["users"] if r["id"] != user_id
            ]
            self._save()


    def add_server(
        self,
        name,
        game,
        description,
        install_dir,
        start_command,
        port,
        owner_id,
        autostart=False,
        memory_limit_mb=0,
        cpu_limit_pct=0,
        disk_limit_mb=0,
        template="custom",
    ):
        with self._lock:
            server = Server(
                id=self._data["_next"]["server"],
                name=name,
                game=game,
                description=description,
                install_dir=install_dir,
                start_command=start_command,
                port=port,
                status="offline",
                pid=0,
                autostart=autostart,
                owner_id=owner_id,
                created_at=datetime.utcnow(),
                memory_limit_mb=memory_limit_mb,
                cpu_limit_pct=cpu_limit_pct,
                disk_limit_mb=disk_limit_mb,
                template=template,
            )
            self._data["_next"]["server"] += 1
            self._data["servers"].append(server.to_dict())
            self._save()
            return server

    def get_server(self, server_id):
        for row in self._data["servers"]:
            if row["id"] == server_id:
                return Server.from_dict(row)
        return None

    def all_servers(self):
        return [Server.from_dict(r) for r in self._data["servers"]]

    def servers_for(self, owner_id):
        return [s for s in self.all_servers() if s.owner_id == owner_id]

    def save_server(self, server):
        with self._lock:
            for i, row in enumerate(self._data["servers"]):
                if row["id"] == server.id:
                    self._data["servers"][i] = server.to_dict()
                    break
            self._save()

    def delete_server(self, server_id):
        with self._lock:
            self._data["servers"] = [
                r for r in self._data["servers"] if r["id"] != server_id
            ]
            self._save()


    def add_log(self, level, action, message, username, ip=None):
        with self._lock:
            entry = {
                "id": self._data["_next"].get("log", 1),
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "level": level,
                "action": action,
                "message": message,
                "username": username or "system",
                "ip": ip,
            }
            self._data["_next"]["log"] = entry["id"] + 1
            self._data["logs"].append(entry)
            if len(self._data["logs"]) > MAX_AUDIT_LOGS:
                del self._data["logs"][: len(self._data["logs"]) - MAX_AUDIT_LOGS]
            self._save()

    def all_logs(self, limit=500, reverse=True):
        logs = sorted(self._data.get("logs", []), key=lambda e: e["id"])
        if reverse:
            logs = list(reversed(logs))
        return logs[:limit]

    def count_logs(self):
        return len(self._data.get("logs", []))

    def clear_logs(self):
        with self._lock:
            self._data["logs"] = []
            self._save()


db = Database(DATA_FILE)
