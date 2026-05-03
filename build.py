"""
Cross-platform build script for Vaultex Gaming Launcher.
Generates standalone executables for Windows, macOS, and Linux using PyInstaller.

Usage:
    python build.py              # Build for current platform
    python build.py --all        # Show instructions for all platforms

Dependencies:
    pip install pyinstaller
"""

import os
import sys
import subprocess
import shutil
import platform


# ── Configuration ──────────────────────────────────────────────────────
APP_NAME = "VaultexLauncher"
MAIN_SCRIPT = "main.py"
ICON_DIR = os.path.join("assets", "icons")
ASSETS_DIR = "assets"
DIST_DIR = "dist"
BUILD_DIR = "build"


def get_platform_name() -> str:
    """Return a normalized platform name."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    return system


def get_icon_path() -> str | None:
    """Return the platform-appropriate icon file path, if it exists."""
    plat = get_platform_name()
    if plat == "windows":
        ico = os.path.join(ICON_DIR, "vaultex.ico")
        return ico if os.path.exists(ico) else None
    elif plat == "macos":
        icns = os.path.join(ICON_DIR, "vaultex.icns")
        return icns if os.path.exists(icns) else None
    else:
        png = os.path.join(ICON_DIR, "vaultex.png")
        return png if os.path.exists(png) else None


def build_pyinstaller_args() -> list[str]:
    """Construct the PyInstaller command line arguments."""
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",              # Single executable
        "--windowed",             # No console window (GUI app)
        "--clean",                # Clean build cache
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
    ]

    # Add icon if available
    icon = get_icon_path()
    if icon:
        args.append(f"--icon={icon}")

    # Bundle the assets directory
    if os.path.isdir(ASSETS_DIR):
        # PyInstaller data format: source;destination (Windows) or source:destination (Unix)
        sep = ";" if sys.platform == "win32" else ":"
        args.append(f"--add-data={ASSETS_DIR}{sep}{ASSETS_DIR}")

    # Platform-specific hidden imports
    if sys.platform == "win32":
        args.extend([
            "--hidden-import=pythoncom",
            "--hidden-import=win32com",
            "--hidden-import=win32com.shell",
        ])

    # Optimize
    args.append("--noconfirm")            # Overwrite output without asking
    # --strip only works on Unix (requires strip binary)
    if sys.platform != "win32":
        args.append("--strip")

    # UPX compression if available
    if shutil.which("upx"):
        args.append("--upx-dir=" + os.path.dirname(shutil.which("upx")))

    # Main script
    args.append(MAIN_SCRIPT)

    return args


def build():
    """Run the PyInstaller build process."""
    plat = get_platform_name()
    print(f"{'=' * 60}")
    print(f"  Vaultex Launcher — Building for {plat.upper()}")
    print(f"{'=' * 60}")

    # Verify main script exists
    if not os.path.isfile(MAIN_SCRIPT):
        print(f"[ERROR] {MAIN_SCRIPT} not found. Run from the project root.")
        sys.exit(1)

    # Verify PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)

    # Build
    args = build_pyinstaller_args()
    print(f"\n[BUILD] Command:\n  {' '.join(args)}\n")

    result = subprocess.run(args, cwd=os.path.dirname(os.path.abspath(__file__)) or ".")

    if result.returncode != 0:
        print(f"\n[FAILED] Build failed with exit code {result.returncode}")
        sys.exit(1)

    # Report output
    if plat == "windows":
        exe_name = f"{APP_NAME}.exe"
    elif plat == "macos":
        exe_name = APP_NAME  # PyInstaller --onefile produces a Unix binary
    else:
        exe_name = APP_NAME

    output_path = os.path.join(DIST_DIR, exe_name)
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"\n{'=' * 60}")
        print(f"  BUILD SUCCESSFUL!")
        print(f"  Output: {os.path.abspath(output_path)}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Platform: {plat}")
        print(f"{'=' * 60}")
    else:
        print(f"\n[WARNING] Build completed but output not found at {output_path}")


def show_cross_platform_instructions():
    """Print instructions for building on each platform."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        VAULTEX LAUNCHER — Cross-Platform Build Guide        ║
╚══════════════════════════════════════════════════════════════╝

Prerequisites (all platforms):
  pip install -r requirements.txt

═══════════════════════════════════════════════════════════════
  WINDOWS
═══════════════════════════════════════════════════════════════
  1. Open PowerShell in the project directory
  2. pip install -r requirements.txt
  3. python build.py
  4. Output: dist/VaultexLauncher.exe

  Note: pywin32 is auto-installed for .lnk shortcut support.

═══════════════════════════════════════════════════════════════
  macOS
═══════════════════════════════════════════════════════════════
  1. Open Terminal in the project directory
  2. pip3 install -r requirements.txt
  3. python3 build.py
  4. Output: dist/VaultexLauncher

  For a .app bundle instead of a single binary:
    pyinstaller --windowed --onedir --name=VaultexLauncher \\
      --add-data="assets:assets" main.py
    # Output: dist/VaultexLauncher.app/

  Note: .lnk shortcut resolution is skipped on macOS (not needed).
        macOS games are .app bundles — drag & drop is supported.

═══════════════════════════════════════════════════════════════
  LINUX
═══════════════════════════════════════════════════════════════
  1. Open terminal in the project directory
  2. pip install -r requirements.txt
  3. python build.py
  4. Output: dist/VaultexLauncher
  5. chmod +x dist/VaultexLauncher  (should be auto-set)

  For AppImage packaging (optional):
    # Install appimagetool
    # Create AppDir structure and package

  Note: Linux games are detected by execute permission (chmod +x).
        Drag & drop any executable file into the launcher.

═══════════════════════════════════════════════════════════════
  GENERAL TIPS
═══════════════════════════════════════════════════════════════
  • UPX: Install UPX (upx.github.io) to compress the binary further.
  • The built executable includes all dependencies — no Python needed.
  • The database (launcher.db) is created next to the executable on first run.
  • Custom fonts in assets/fonts/ are bundled automatically.
""")


if __name__ == "__main__":
    if "--all" in sys.argv or "--help" in sys.argv:
        show_cross_platform_instructions()
    else:
        build()
