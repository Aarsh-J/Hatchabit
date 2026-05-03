#!/usr/bin/env python3
"""TaskFlow — run this to start the app."""
import os, sys, subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    import flask
except ImportError:
    print("Installing Flask...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])

from app import app, ensure_files
import webbrowser, threading

ensure_files()
print("\n✦ TaskFlow running at http://localhost:5050")
print("  Press Ctrl+C to stop.\n")
threading.Timer(0.8, lambda: webbrowser.open("http://localhost:5050")).start()
app.run(port=5050, debug=False)
