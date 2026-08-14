import os
import shutil
import subprocess
import threading
import time

from .server_templates import resolve_command

MAX_BUFFER = 2000
LIMIT_STRIKES = 5
LIMIT_INTERVAL = 15


def _tree_procs(pid):
    """Return the process and all its descendants (handles shell=True wrappers)."""
    try:
        import psutil

        parent = psutil.Process(pid)
        return [parent] + parent.children(recursive=True)
    except Exception:
        return []


class ServerProcess:
    """Wraps one running game-server subprocess and its console log buffer."""

    def __init__(self, server_id):
        self.server_id = server_id
        self.gen = 0
        self.process = None
        self.on_exit = None
        self.on_limit = None
        self._net_prev = None
        self._net_delta = None
        self._limit_strikes = 0
        self._limit_reason = ""
        self._lock = threading.Lock()
        self._logs = []
        self._log_seq = 0


    def is_running(self):
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def logs_since(self, after, limit=250):
        with self._lock:
            lo, hi = 0, len(self._logs)
            while lo < hi:
                mid = (lo + hi) // 2
                if self._logs[mid][0] <= after:
                    lo = mid + 1
                else:
                    hi = mid
            items = self._logs[lo:]
            if len(items) > limit:
                items = items[-limit:]
            return list(items)


    def start(self, command, cwd, env):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return False
            self.gen += 1
            gen = self.gen
            self._logs = []
            self._log_seq = 0
            self._net_prev = None
            self._net_delta = None
            try:
                self.process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )
            except OSError as exc:
                self.process = None
                raise RuntimeError(str(exc))
        threading.Thread(target=self._reader, args=(gen,), daemon=True).start()
        return True

    def _reader(self, gen):
        proc = self.process
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                self._push(line)
        except (OSError, ValueError):
            pass
        code = proc.returncode
        self._push(f"[Process exited with code {code}]\n")
        with self._lock:
            self.process = None
        if self.on_exit:
            self.on_exit(gen)

    def stop(self, timeout=15):
        with self._lock:
            proc = self.process
            if proc is None or proc.poll() is not None:
                self.process = None
                return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass

    def kill(self):
        with self._lock:
            proc = self.process
            if proc is None or proc.poll() is not None:
                self.process = None
                return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=5,
                )
            else:
                proc.kill()
        except Exception:
            pass


    def send_command(self, command):
        with self._lock:
            proc = self.process
        if proc is None or proc.poll() is not None:
            return False
        try:
            proc.stdin.write(command + "\n")
            proc.stdin.flush()
            self._push("> " + command + "\n")
            return True
        except (OSError, ValueError):
            return False

    def start_watchdog(self, mem_limit_mb, cpu_limit_pct, gen):
        if not (mem_limit_mb or cpu_limit_pct):
            return
        threading.Thread(
            target=self._watchdog,
            args=(mem_limit_mb, cpu_limit_pct, gen),
            daemon=True,
        ).start()

    def _watchdog(self, mem_limit_mb, cpu_limit_pct, gen):
        try:
            import psutil
        except Exception:
            return
        while self.gen == gen and self.is_running():
            procs = _tree_procs(self.process.pid)
            if not procs:
                break
            for p in procs:
                try:
                    p.cpu_percent(None)
                except psutil.Error:
                    pass
            time.sleep(LIMIT_INTERVAL)
            if self.gen != gen or not self.is_running():
                break
            procs = _tree_procs(self.process.pid)
            if not procs:
                break
            cpu = 0.0
            mem = 0.0
            for p in procs:
                try:
                    cpu += p.cpu_percent(None)
                    mem += p.memory_info().rss
                except psutil.Error:
                    pass
            mem /= 1048576
            reasons = []
            if mem_limit_mb and mem > mem_limit_mb:
                reasons.append(f"memory {mem:.0f}/{mem_limit_mb} MB")
            if cpu_limit_pct and cpu > cpu_limit_pct:
                reasons.append(f"CPU {cpu:.1f}/{cpu_limit_pct}%")
            if reasons:
                self._limit_strikes += 1
                self._limit_reason = ", ".join(reasons)
                self._push(
                    "\x1b[33m[limit] "
                    + self._limit_reason
                    + f" exceeded - warning {self._limit_strikes}/{LIMIT_STRIKES}, "
                    + "server will be stopped if it continues\x1b[0m\n"
                )
                if self.on_limit:
                    try:
                        self.on_limit(self._limit_reason, self._limit_strikes)
                    except Exception:
                        pass
                if self._limit_strikes >= LIMIT_STRIKES:
                    self._push(
                        "\x1b[31m[limit] stopping server: "
                        + self._limit_reason
                        + " over limit\x1b[0m\n"
                    )
                    self.stop()
                    break
            else:
                self._limit_strikes = 0
                self._limit_reason = ""

    def _push(self, text):
        with self._lock:
            self._log_seq += 1
            self._logs.append((self._log_seq, text))
            if len(self._logs) > MAX_BUFFER:
                del self._logs[: len(self._logs) - MAX_BUFFER]


class ServerManager:
    """Registry of active ServerProcess objects for the whole app."""

    def __init__(self, app=None):
        self.app = app
        self._procs = {}
        self._lock = threading.Lock()
        self._size_cache = {}
        self._size_cache_ttl = 5.0

    def get(self, server_id):
        with self._lock:
            return self._procs.get(server_id)

    def _register(self, server_id):
        with self._lock:
            sp = self._procs.get(server_id)
            if sp is None:
                sp = ServerProcess(server_id)
                self._procs[server_id] = sp
            return sp

    def status(self, server):
        sp = self.get(server.id)
        return "running" if sp and sp.is_running() else "offline"

    def start(self, server):
        sp = self._register(server.id)
        sp.on_exit = lambda gen, sid=server.id: self._on_exit(sid, gen)
        if not os.path.isdir(server.install_dir):
            raise RuntimeError(
                f"Install directory not found: {server.install_dir}"
            )
        if server.disk_limit_mb:
            size = self.folder_size_mb(server.id, server.install_dir)
            if size is not None and size > server.disk_limit_mb:
                raise RuntimeError(
                    f"Folder size {size:.0f} MB exceeds the "
                    f"{server.disk_limit_mb} MB storage limit"
                )
        env = os.environ.copy()
        env["SERVER_PORT"] = str(server.port)
        env["SERVER_NAME"] = server.name
        env["PYTHONUNBUFFERED"] = "1"
        command = resolve_command(server)
        if not sp.start(command, server.install_dir, env):
            raise RuntimeError("Server is already running")
        sp.on_limit = lambda reason, strikes, sid=server.id: self._audit_limit(
            sid, reason, strikes
        )
        sp.start_watchdog(
            server.memory_limit_mb, server.cpu_limit_pct, sp.gen
        )
        self._set_status(server.id, "running")
        return True

    def stop(self, server):
        sp = self.get(server.id)
        if sp is None:
            return False
        sp.on_exit = lambda gen, sid=server.id: self._on_exit(sid, gen)
        sp.stop()
        return True

    def kill(self, server):
        sp = self.get(server.id)
        if sp is None:
            return False
        sp.on_exit = lambda gen, sid=server.id: self._on_exit(sid, gen)
        sp.kill()
        self._set_status(server.id, "offline")
        return True

    def get_stats(self, server):
        sp = self.get(server.id)
        running = bool(sp and sp.is_running())
        stats = {
            "status": "running" if running else "offline",
            "cpu": None,
            "memory": None,
            "disk": None,
            "network": None,
            "uptime": None,
            "players": None,
            "folder": None,
        }
        if running and sp and sp.process:
            stats.update(self._process_stats(sp))
        disk = self._disk_stats(server.install_dir)
        if disk:
            stats["disk"] = disk
        size = self.folder_size_mb(server.id, server.install_dir)
        if size is not None:
            stats["folder"] = {
                "used_mb": round(size, 1),
                "limit_mb": server.disk_limit_mb,
            }
        if sp is not None and sp._limit_strikes:
            stats["limit"] = {
                "strikes": sp._limit_strikes,
                "reason": sp._limit_reason,
                "max": LIMIT_STRIKES,
            }
        return stats

    def folder_size_mb(self, server_id, install_dir):
        try:
            cached = self._size_cache.get(server_id)
            if cached and time.time() - cached[0] < self._size_cache_ttl:
                return cached[1]
        except Exception:
            cached = None
        try:
            total = 0
            for root, _dirs, files in os.walk(install_dir):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass
        except OSError:
            return None
        size_mb = total / 1048576
        self._size_cache[server_id] = (time.time(), size_mb)
        return size_mb

    def _process_stats(self, sp):
        result = {"cpu": None, "memory": None, "network": None, "uptime": None}
        try:
            import psutil

            procs = _tree_procs(sp.process.pid)
            if not procs:
                return result
            for p in procs:
                try:
                    p.cpu_percent(None)
                except psutil.Error:
                    pass
            time.sleep(0.3)
            cpu = 0.0
            rss = 0
            for p in procs:
                try:
                    cpu += p.cpu_percent(None)
                    rss += p.memory_info().rss
                except psutil.Error:
                    pass
            mem = rss / 1048576
            total = psutil.virtual_memory().total / 1048576
            result["cpu"] = round(cpu, 1)
            result["memory"] = {
                "used_mb": round(mem, 1),
                "total_mb": round(total, 1),
            }
            result["uptime"] = int(time.time() - procs[0].create_time())

            now = time.time()
            net = psutil.net_io_counters()
            if sp._net_prev is not None:
                prev_t, prev_s, prev_r = sp._net_prev
                dt = max(now - prev_t, 0.1)
                sp._net_delta = {
                    "rx_kbs": round(max(0, net.bytes_recv - prev_r) / dt / 1024, 2),
                    "tx_kbs": round(max(0, net.bytes_sent - prev_s) / dt / 1024, 2),
                }
            sp._net_prev = (now, net.bytes_sent, net.bytes_recv)
            if sp._net_delta:
                result["network"] = sp._net_delta
        except Exception:
            pass
        return result

    def _disk_stats(self, install_dir):
        try:
            usage = shutil.disk_usage(install_dir)
            return {
                "total_mb": round(usage.total / 1048576, 1),
                "used_mb": round(usage.used / 1048576, 1),
                "free_mb": round(usage.free / 1048576, 1),
                "used_pct": round(usage.used / usage.total * 100, 1),
            }
        except OSError:
            return None

    def restart(self, server):
        sp = self.get(server.id)
        if sp is not None:
            sp.stop()
            for _ in range(100):
                if not sp.is_running():
                    break
                time.sleep(0.05)
        self.start(server)

    def _on_exit(self, server_id, gen):
        sp = self.get(server_id)
        if sp is None or sp.gen != gen:
            return
        self._set_status(server_id, "offline")

    def _audit_limit(self, server_id, reason, strikes):
        if self.app is None:
            return
        from .audit import audit
        from .storage import db

        server = db.get_server(server_id)
        name = server.name if server else f"#{server_id}"
        message = f'"{name}" {reason} over limit (warning {strikes}/{LIMIT_STRIKES})'
        level = "error" if strikes >= LIMIT_STRIKES else "warn"
        try:
            with self.app.app_context():
                audit("limit", message, level=level, username="watchdog")
        except Exception:
            pass

    def _set_status(self, server_id, status):
        if self.app is None:
            return
        from .storage import db

        server = db.get_server(server_id)
        if server is not None:
            server.status = status
            if status == "offline":
                server.pid = 0
            else:
                sp = self.get(server_id)
                if sp and sp.process:
                    server.pid = sp.process.pid or 0
            db.save_server(server)

    def autostart(self):
        if self.app is None:
            return
        from .storage import db

        servers = [s for s in db.all_servers() if s.autostart]
        for server in servers:
            try:
                self.start(server)
            except Exception as exc:
                print(f"[autostart] {server.name}: {exc}")
