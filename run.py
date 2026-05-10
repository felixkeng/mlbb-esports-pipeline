import os
import subprocess
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = "http://127.0.0.1:8000"

routes = [
    ("Root",            "/"),
    ("All Matches",     "/matches"),
    ("Tournaments",     "/tournaments"),
    ("Standings",       "/standings"),
    ("Team Form",       "/form/ONIC"),
    ("Head to Head",    "/h2h?team_a=ONIC&team_b=RRQ Hoshi"),
    ("All Heroes",      "/heroes"),
    ("Top Heroes",      "/heroes/top"),
    ("Hero Detail",     "/heroes/Gloo"),
    ("Hero Counters",   "/counters/Gloo"),
    ("API Docs",        "/docs"),
    ("Draft Website",    "/ui"),
]

print("\n🎮 MLBB Esports API\n")
print("Available endpoints:")
for name, path in routes:
    print(f"  {name:<20} {BASE}{path}")
print()

subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload"])