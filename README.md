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

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
