import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PANEL_PORT", "8080"))
    print(f"")
    print(f"  BytePanel is running at http://localhost:{port}")
    print(f"  First time? Open the URL and register the admin account.")
    print(f"  Press Ctrl+C to stop the panel.")
    print(f"")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
