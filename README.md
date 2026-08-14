# BytePanel

A self-hosted, lightweight **game-server management panel** built with Flask. Launch, monitor and control game servers straight from a slick dark-glass web UI — with live graphs, a colorized console, a file manager and per-server resource limits.

> Designed for small game hosts, home labs and anyone running Minecraft, Valheim, Terraria, Python bots or any custom process. All data is stored in a simple JSON file — no database server required.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)
![License](https://img.shields.io/badge/License-Apache%202.0-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

---
#Warning: Default Admin usernaem and password is admin admin
## Features

### Server management
- Create, edit, delete and start **any game server** by running a custom start command (Java, Python, Node, binaries…).
- **Start / Stop / Restart / Kill** controls with safe force-kill on Windows (`taskkill /T /F`).
- **Autostart** servers when the panel boots.
- Per-server owners and an **admin / owner permission model**.

### Live monitoring
- Real-time **CPU, memory, disk and network** stats.
- **Sparklines + history graphs** rendered on a canvas — no charting library needed.
- Live **uptime** and a **players** slot (for game APIs later).

### Console
- **Live streaming console** with real-time output.
- **ANSI color rendering** (basic, 256-color and truecolor) so Minecraft / Paper logs look native.
- Send commands, clear, auto-scroll, and a **kill** button when a server hangs.
- **Batched rendering** — stays smooth even with a 2000-line buffer.

### File manager
- Browse the server folder in the browser.
- **Edit** text files inline, **upload / create / rename / delete** files.
- Path-traversal-safe (`safe_join` guard).

### Resource limits (new)
Cap runaway servers and protect the host:

| Limit | What it does | Unit |
|---|---|---|
| **Memory limit** | Watchdog force-stops the server if it stays over the cap (3 warnings first) | MB |
| **CPU limit** | Watchdog force-stops the server if it stays over the cap (`100` = one full core) | % |
| **Storage limit** | Blocks *starting* the server once its folder exceeds the cap | MB |

- Live **usage-vs-limit bars** on the server overview.
- Limit violations are written to the console in color before the server is stopped.
- `0` means unlimited.

### Design
- Dark **glassy UI**, Lucide icons, fully responsive with a mobile slide-in sidebar.
- No heavy JS frameworks — vanilla JS + canvas.

### Audit logs
- Every important event is recorded and viewable under **Admin → Logs**:
  **logins / failed logins, logouts, new members**, user & server changes, file edits/uploads/deletes, commands sent, limit warnings.
- Level badges (info / warn / error), live search + filter, and a clear button.
- Stored in `instance/data.json` (last 1000 entries, auto-trimmed).

---

## Screenshots

*Screenshots coming soon. Start the panel and log in to see the dashboard, live graphs, console and file manager in action.*

---

## Quick start (Windows)

> BytePanel ships with one-click batch scripts.

```bat
install.bat   :: creates a venv and installs dependencies
start.bat     :: launches the panel on http://localhost:8080
```

1. Install **Python 3.9+** (check *"Add python.exe to PATH"*).
2. Run `install.bat`.
3. Run `start.bat`.
4. Open **http://localhost:8080** and register the first account — it becomes **admin**.

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py          # serves on http://localhost:8080
```

You can change the port with an env var:

```bash
PANEL_PORT=9000 python run.py
```

---

## First steps

1. Register → first account is the **admin**.
2. **Admin → Users** → create a normal user (or use the admin account for everything).
3. **Admin → Servers → New server**:
   - **Name** + **port** (must be unique).
   - **Owner** — the user who can manage it.
   - **Start command** — runs inside the server folder. Env vars available: `SERVER_PORT`, `SERVER_NAME`.
     - e.g. Minecraft: `java -Xmx1G -jar server.jar nogui`
     - e.g. Python: tick *"create a virtual environment"* → defaults to `venv\Scripts\python.exe main.py`.
   - Optional **resource limits** (MB / % / MB).
4. Open the server → **Start**, then open the **console** and **file manager**.

---

## Roles & permissions

| Role | Can do |
|---|---|
| **Admin** | Everything: manage all users, all servers, set limits, delete with files |
| **Owner** | Manage the servers assigned to them (start/stop/console/files/settings) |
| **Other users** | See only the servers they own (dashboard) |

---

## API endpoints

### Remote admin API

URL-style REST API. The key is the **admin account's password** (any admin account works).

```text
# Create a user
GET  /api/admin/<admin_password>/adduser/<username>/<password>

# Create a server (JSON POST also accepted)
GET  /api/admin/<admin_password>/addserver/<name>/<port>

# Server status
GET  /api/admin/<admin_password>/status/<server_id>
```

Examples (with an admin whose password is `admin`):

```text
127.0.0.1:8080/api/admin/admin/adduser/Annie/Annieishere
127.0.0.1:8080/api/admin/admin/addserver/MyServer/25565?game=Minecraft
```

`addserver` accepts these query / JSON parameters (all optional except name & port):

| Parameter | Default | Meaning |
|---|---|---|
| `owner` | the calling admin | username of the server owner |
| `game` | `Custom` | Game / software label |
| `start_command` | `python.exe main.py` (Windows) / `python3 main.py` | Command to run |
| `create_dir` | `1` | Create the server folder if missing |
| `autostart` | `0` | Start server when panel boots |
| `memory_limit_mb` | `0` (unlimited) | Memory limit |
| `cpu_limit_pct` | `0` (unlimited) | CPU limit (`100` = one core) |
| `disk_limit_mb` | `0` (unlimited) | Storage limit |

Responses are JSON: `{"ok": true, ...}` on success, or `{"ok": false, "error": "..."}` with the right status code (`401` bad key, `400` bad input, `409` duplicate, `404` missing).

> **Note:** the key travels in the URL, so it can leak into logs/proxies. Only use this on a trusted network, or put the panel behind a reverse proxy. A dedicated token-based auth is planned for a future release.

### UI JSON endpoints

Used by the live dashboard (require a browser session):

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/servers/<id>/api/status` | Running / offline |
| `GET` | `/servers/<id>/api/stats` | cpu, memory, disk, network, uptime, folder size + limits |
| `GET` | `/servers/<id>/api/logs?after=<seq>` | New console lines since a sequence number (capped) |
| `POST` | `/servers/<id>/api/command` | Send a command to stdin `{"command": "..."}` |
| `POST` | `/servers/<id>/start` `/stop` `/restart` `/kill` | Lifecycle controls |
| `GET` | `/servers/<id>/settings` | View / edit startup settings |
| `GET/POST` | `/files/...` | File manager |

---

## Project structure

```
BytePanel/
├── app/
│   ├── __init__.py          # app factory, blueprints, context processors
│   ├── config.py            # paths & constants
│   ├── models.py            # User / Server (plain classes, no ORM)
│   ├── storage.py           # JSON-file database (thread-safe, atomic saves)
│   ├── server_manager.py    # process control, log buffer, stats, watchdog
│   ├── audit.py             # audit-log helper
│   ├── routes/
│   │   ├── auth.py          # login / register
│   │   ├── main.py          # dashboard
│   │   ├── admin.py         # users, servers & logs CRUD
│   │   ├── api.py           # remote admin API
│   │   ├── servers.py       # detail, console, settings, APIs
│   │   └── files.py         # file manager
│   ├── templates/           # Jinja2 pages
│   └── static/
│       ├── css/style.css    # design system
│       └── js/              # panel.js, server.js, console.js, files.js
├── instance/data.json       # users + servers (auto-created)
├── servers/                 # created server folders
├── run.py                   # entry point
├── install.bat / start.bat  # Windows bootstrap
└── requirements.txt
```

---

## Tech stack

- **Flask 3** + **Jinja2** server-rendered pages
- **Flask-Login** for auth (bcrypt-hashed passwords)
- **psutil** for live process / system stats
- **Vanilla JS + Canvas** for graphs and console
- **JSON-file storage** — zero-config, portable

---

## Why no database?

BytePanel keeps everything in one human-readable JSON file (`instance/data.json`) with atomic writes and a lock. For a handful of servers this is simpler and easier to back up than a full SQL database. If you outgrow it, the `storage.py` layer is the single place to swap in a real DB.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Server won't start: *"Install directory not found"* | Create the folder on disk first (or tick *"create the directory now"*). |
| Server won't start: *"Folder size exceeds the storage limit"* | Increase the storage limit or clean up the folder. |
| Console shows garbled characters | Server output is encoded as UTF-8; older Windows tools may need `chcp 65001`. |
| Port already in use | Pick a different port in the server settings. |
| `psutil` fails to install on 32-bit Python | Keep the pinned `psutil==7.1.1` in `requirements.txt`. |

---

## Roadmap

- [ ] Scheduled tasks (auto-restart on crash, backups)
- [x] Server templates for common games (Minecraft, Valheim, Terraria)
- [ ] Per-user dashboard quotas
- [ ] Webhooks / Discord notifications on limit violations

---

## License

Apache License 2.0
