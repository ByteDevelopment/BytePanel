"""Predefined server run-command templates.

Each template describes how a freshly created server is launched. A template
may declare a ``{{RAM}}`` placeholder in its command; when such a server is
started the placeholder is automatically replaced with the server's configured
``memory_limit_mb`` value (falling back to ``DEFAULT_RAM_MB`` when the limit is
unset), so an administrator only has to set the memory limit and the Minecraft
JVM flags are adjusted automatically.
"""

DEFAULT_RAM_MB = 1024

MINECRAFT_COMMAND = (
    "java -Xms{{RAM}}M -Xmx{{RAM}}M -XX:+UseG1GC -XX:+ParallelRefProcEnabled "
    "-XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC "
    "-XX:+AlwaysPreTouch -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 "
    "-XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 "
    "-XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem "
    "-XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs "
    "-Daikars.new.flags=true -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 "
    "-XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -jar server.jar --nogui"
)

PYTHON_COMMAND = "pip install -r requirements.txt && python3 main.py"


def _python_command():
    """Return the platform-aware Python run command."""
    if __import__("os").name == "nt":
        return "pip install -r requirements.txt && python main.py"
    return PYTHON_COMMAND


SERVER_TEMPLATES = {
    "minecraft": {
        "name": "Minecraft",
        "game": "Minecraft",
        "command": MINECRAFT_COMMAND,
        "has_ram_placeholder": True,
        "hint": "Memory limit (MB) is injected into -Xms/-Xmx automatically.",
    },
    "python": {
        "name": "Python",
        "game": "Python",
        "command": _python_command(),
        "has_ram_placeholder": False,
        "hint": "Installs requirements.txt then runs the app on every start.",
    },
    "custom": {
        "name": "Custom",
        "game": "",
        "command": "",
        "has_ram_placeholder": False,
        "hint": "Write your own start command.",
    },
}


def get_template(key):
    """Return the template dict for ``key`` or the ``custom`` fallback."""
    return SERVER_TEMPLATES.get(key, SERVER_TEMPLATES["custom"])


def list_templates():
    """Return an ordered list of (key, template) tuples for rendering."""
    return list(SERVER_TEMPLATES.items())


def resolve_command(server):
    """Resolve the effective start command for ``server``.

    For templates that declare a ``{{RAM}}`` placeholder the token is replaced
    with the server's ``memory_limit_mb`` (or ``DEFAULT_RAM_MB`` when unset) on
    every start, so changing the memory limit takes effect immediately without
    re-editing the command. The same substitution is applied whenever the
    ``{{RAM}}`` token appears in a custom command, so memory limits always win.
    """
    template = get_template(getattr(server, "template", "") or "")
    command = server.start_command or template["command"]
    if "{{RAM}}" in command:
        ram = getattr(server, "memory_limit_mb", 0) or DEFAULT_RAM_MB
        command = command.replace("{{RAM}}", str(ram))
    return command
