#!/usr/bin/env python3
"""Hatchabit — run this to start the app locally."""
import os
import subprocess
import sys
import threading
import webbrowser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    import flask  # noqa: F401
except ImportError:
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

from app import app

print("\n✦ Hatchabit running at http://localhost:5050")
print("  Press Ctrl+C to stop.\n")
threading.Timer(0.8, lambda: webbrowser.open("http://localhost:5050")).start()
app.run(port=5050, debug=False)
