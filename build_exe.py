"""Build BlackBoxAF as a standalone Windows .exe using PyInstaller."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
FRONTEND = SRC / "blackboxaf" / "frontend"
ENTRY = ROOT / "run.py"
ICON = ROOT / "icon.ico"  # Optional: add an icon file if you have one


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "BlackBoxAF",
        "--onefile",
        "--console",  # Keep console for log output; use --windowed for silent
        # Tell PyInstaller where to find the blackboxaf package
        "--paths", str(SRC),
        # Bundle the frontend directory as data files
        "--add-data", f"{FRONTEND};frontend",
        # Hidden imports that PyInstaller may miss
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        # Clean build
        "--clean",
        "--noconfirm",
    ]

    # Add icon if it exists
    if ICON.exists():
        cmd.extend(["--icon", str(ICON)])

    # Entry point
    cmd.append(str(ENTRY))

    print("Building BlackBoxAF.exe...")
    print(f"  Entry: {ENTRY}")
    print(f"  Frontend: {FRONTEND}")
    print()

    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode == 0:
        exe_path = ROOT / "dist" / "BlackBoxAF.exe"
        print()
        print(f"  Build successful!")
        print(f"  Output: {exe_path}")
        print(f"  Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        print()
        print("  To run: double-click BlackBoxAF.exe or run from terminal")
        print("  The database (data/blackboxaf.db) will be created next to the .exe")
    else:
        print(f"  Build failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
