import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
SERVERS_DIR = os.path.join(BASE_DIR, "servers")
DB_PATH = os.path.join(INSTANCE_DIR, "panel.db")
DATA_FILE = os.path.join(INSTANCE_DIR, "data.json")
SECRET_FILE = os.path.join(INSTANCE_DIR, "secret.key")
MAX_CONSOLE_LINES = 2000
DEFAULT_PANEL_PORT = 8080
