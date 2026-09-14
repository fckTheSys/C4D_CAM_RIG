"""Install the private CK_CAM plugin folder without modifying source scenes."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


FILES = ("builder.py", "runtime.py", "motion_math.py", "path_math.py", "curve_math.py",
         "create_simple_camera.py", "select_camera.py", "update_selected_rig.py", "README.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install private Chiken_CAM (CK_CAM) for C4D.")
    parser.add_argument("--plugins-dir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "prototypes" / "simple_camera"
    destination = args.plugins_dir.resolve() / "Chiken_CAM"
    if destination.exists():
        raise FileExistsError("Refusing to overwrite existing installation: " + str(destination))
    if not (root / "Chiken_CAM" / "CK_CAM.pyp").is_file():
        raise RuntimeError("CK_CAM.pyp is missing")
    missing = [name for name in FILES if not (source / name).is_file()]
    if missing:
        raise RuntimeError("Missing source files: " + ", ".join(missing))
    destination.mkdir(parents=True)
    shutil.copy2(root / "Chiken_CAM" / "CK_CAM.pyp", destination / "CK_CAM.pyp")
    runtime = destination / "prototypes" / "simple_camera"
    runtime.mkdir(parents=True)
    for name in FILES:
        shutil.copy2(source / name, runtime / name)
    print("Installed Chiken_CAM to " + str(destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
