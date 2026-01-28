"""Build script for ReadIn AI (Cross-platform)."""

import subprocess
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def clean():
    """Clean previous build artifacts."""
    print("Cleaning previous builds...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    print("Clean complete")


def create_ico():
    """Convert PNG icon to ICO format (Windows only)."""
    if not IS_WINDOWS:
        return

    try:
        from PIL import Image

        png_path = PROJECT_ROOT / "assets" / "icon.png"
        ico_path = PROJECT_ROOT / "assets" / "icon.ico"

        if png_path.exists() and not ico_path.exists():
            print("Creating icon.ico...")
            img = Image.open(png_path)
            img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print("Icon created")
    except ImportError:
        print("PIL not available, skipping ICO creation")
    except Exception as e:
        print(f"Icon creation failed: {e}")


def create_icns():
    """Convert PNG icon to ICNS format (macOS only)."""
    if not IS_MACOS:
        return

    png_path = PROJECT_ROOT / "assets" / "icon.png"
    icns_path = PROJECT_ROOT / "assets" / "icon.icns"

    if png_path.exists() and not icns_path.exists():
        print("Creating icon.icns...")
        try:
            # Create iconset directory
            iconset_dir = PROJECT_ROOT / "assets" / "icon.iconset"
            iconset_dir.mkdir(exist_ok=True)

            # Generate different sizes using sips
            sizes = [16, 32, 64, 128, 256, 512]
            for size in sizes:
                subprocess.run([
                    "sips", "-z", str(size), str(size),
                    str(png_path), "--out", str(iconset_dir / f"icon_{size}x{size}.png")
                ], capture_output=True)
                # Also create @2x versions
                subprocess.run([
                    "sips", "-z", str(size*2), str(size*2),
                    str(png_path), "--out", str(iconset_dir / f"icon_{size}x{size}@2x.png")
                ], capture_output=True)

            # Convert iconset to icns
            subprocess.run(["iconutil", "-c", "icns", str(iconset_dir)], check=True)

            # Cleanup iconset
            shutil.rmtree(iconset_dir)
            print("Icon created")
        except Exception as e:
            print(f"ICNS creation failed: {e}")


def build():
    """Build the executable."""
    print(f"Building ReadIn AI for {sys.platform}...")

    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "build.spec"
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print("\nBuild successful!")
        if IS_WINDOWS:
            print(f"Output: {DIST_DIR / 'ReadInAI'}")
        elif IS_MACOS:
            print(f"Output: {DIST_DIR / 'ReadInAI.app'}")
        else:
            print(f"Output: {DIST_DIR / 'ReadInAI'}")
    else:
        print("\nBuild failed!")
        sys.exit(1)


def create_installer():
    """Create platform-specific installer."""
    if IS_WINDOWS:
        # Check for Inno Setup
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]
        iscc_path = None
        for path in iscc_paths:
            if Path(path).exists():
                iscc_path = path
                break

        if iscc_path:
            print("Creating Windows installer...")
            result = subprocess.run([iscc_path, "installer.iss"], cwd=PROJECT_ROOT)
            if result.returncode == 0:
                print(f"Installer created: {PROJECT_ROOT / 'installer_output'}")
        else:
            print("Inno Setup not found. Skipping installer creation.")
            print("Download from: https://jrsoftware.org/isdl.php")

    elif IS_MACOS:
        print("Creating macOS DMG...")
        dmg_path = DIST_DIR / "ReadInAI.dmg"
        try:
            subprocess.run([
                "hdiutil", "create",
                "-volname", "ReadIn AI",
                "-srcfolder", str(DIST_DIR / "ReadInAI.app"),
                "-ov", "-format", "UDZO",
                str(dmg_path)
            ], check=True)
            print(f"DMG created: {dmg_path}")
        except Exception as e:
            print(f"DMG creation failed: {e}")

    elif IS_LINUX:
        print("Creating Linux tarball...")
        tarball_path = DIST_DIR / "ReadInAI-Linux.tar.gz"
        try:
            subprocess.run([
                "tar", "-czvf", str(tarball_path),
                "-C", str(DIST_DIR), "ReadInAI"
            ], check=True)
            print(f"Tarball created: {tarball_path}")
        except Exception as e:
            print(f"Tarball creation failed: {e}")


if __name__ == "__main__":
    clean()

    if IS_WINDOWS:
        create_ico()
    elif IS_MACOS:
        create_icns()

    build()

    if "--installer" in sys.argv:
        create_installer()
