# -*- coding: utf-8 -*-
"""
Production-сборка Cam Rig Builder:

  - Копия в …/release/CamRig_<версия>_production/
  - По умолчанию: camrig/*.py → bytecode (-OO), затем удаление .py кроме tag_embedded.py и __init__.py
    (rig_assemble читает tag_embedded.py через open() для TPYTHON_CODE)
  - --sources-only: полные .py без compileall/strip (работает с любым Python C4D)
  - Если --python не задан, на Windows пробуется типичный python.exe из Maxon Cinema 4D …/libs/
  - cam_rig_builder.pyp остаётся; ud_template.json сохраняется
  - LICENSE_COMMERCIAL.txt, README_PRODUCTION.txt

См. tools/PRODUCTION_NOTES.md
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# tag_embedded.py — текст для Python Tag; __init__.py — пакет camrig (иначе from camrig import config падает)
KEEP_PY_SOURCES = frozenset({"tag_embedded.py", "__init__.py"})
SKIP_DIR_NAMES = frozenset({".git", ".serena", "__pycache__", ".pytest_cache", ".cursor", "tools", "release", "tests"})


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _find_c4d_python_exe() -> Path | None:
    """Типичный путь python.exe в установке Maxon Cinema 4D (Windows)."""
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    for year in ("2026", "2025", "2024", "2023"):
        base = pf / ("Maxon Cinema 4D " + year)
        if not base.is_dir():
            continue
        bundled = base / "resource/modules/python/libs/win64/python.exe"
        if bundled.is_file():
            return bundled
        for sub in ("python311", "python310", "python312", "python313"):
            exe = base / "resource" / "modules" / "python" / "libs" / sub / "python.exe"
            if exe.is_file():
                return exe
            fw = base / "resource" / "modules" / "python" / "libs" / (sub + ".win64.framework") / "python.exe"
            if fw.is_file():
                return fw
    return None


def _read_version(root: Path) -> str:
    text = (root / "camrig" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'PLUGIN_VERSION:\s*str\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        m = re.search(r'PLUGIN_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        raise RuntimeError("PLUGIN_VERSION not found in camrig/config.py")
    return m.group(1).strip()


def _copy_sources(src: Path, dst: Path, keep_docs: bool) -> None:
    if dst.exists():
        raise FileExistsError("Refusing to overwrite an existing bundle: %s" % dst)
    dst.mkdir(parents=True)
    for item in src.iterdir():
        name = item.name
        if name in SKIP_DIR_NAMES:
            continue
        if item.is_dir():
            if name not in ("camrig", "res", "docs"):
                continue
            if name == "docs" and not keep_docs:
                continue
            shutil.copytree(item, dst / name, ignore=shutil.ignore_patterns("__pycache__", ".serena", ".cursor", "*.pyc", "*.log", "*.c4d", "baseline-*.json", "INFRASTRUCTURE_AUDIT*"))
        else:
            if name not in ("cam_rig_builder.pyp", "README.md", "INSTALL.md", "CHANGELOG.md", "LICENSE"):
                continue
            if name.endswith(".md") and not keep_docs:
                continue
            shutil.copy2(item, dst / name)


def _strip_camrig_sources(camrig_dir: Path) -> list[Path]:
    removed: list[Path] = []
    for py in sorted(camrig_dir.glob("*.py")):
        if py.name in KEEP_PY_SOURCES:
            continue
        py.unlink()
        removed.append(py)
    return removed


def _compile_bytecode(pkg_dir: Path, python_exe: Path | None) -> None:
    exe = str(python_exe) if python_exe is not None else sys.executable
    r = subprocess.run(
        [exe, "-OO", "-m", "compileall", "-f", "-q", str(pkg_dir)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError("compileall failed (%s):\n%s\n%s" % (exe, r.stdout, r.stderr))


def _verify_layout(dest: Path) -> None:
    cr = dest / "camrig"
    pyc_dir = cr / "__pycache__"
    pyc = list(pyc_dir.glob("*.pyc")) if pyc_dir.is_dir() else []
    if len(pyc) < 6:
        raise RuntimeError("Too few .pyc in camrig/__pycache__ (got %s)" % len(pyc))
    stray = [p.name for p in cr.glob("*.py") if p.name not in KEEP_PY_SOURCES]
    if stray:
        raise RuntimeError("Unexpected .py in camrig/: %s" % ", ".join(stray))
    if not (cr / "ud_template.json").is_file():
        raise RuntimeError("ud_template.json missing")
    if not (cr / "tag_embedded.py").is_file():
        raise RuntimeError("tag_embedded.py missing")
    if not (dest / "cam_rig_builder.pyp").is_file():
        raise RuntimeError("cam_rig_builder.pyp missing")
    print("Layout OK: %s bytecode modules, tag_embedded.py preserved." % len(pyc))


def _verify_layout_sources_only(dest: Path) -> None:
    """Сборка без bytecode: все ключевые .py на месте."""
    cr = dest / "camrig"
    for name in (
        "__init__.py",
        "config.py",
        "rig_builder.py",
        "rig_assemble.py",
        "tag_embedded.py",
        "ud_template.json",
    ):
        if not (cr / name).is_file():
            raise RuntimeError("sources-only: отсутствует camrig/%s" % name)
    if not (dest / "cam_rig_builder.pyp").is_file():
        raise RuntimeError("cam_rig_builder.pyp missing")
    print("Layout OK (sources-only): полные исходники camrig/*.py для любой версии Python C4D.")


def _write_artifacts(dst: Path, version: str, sources_only: bool = False) -> None:
    (dst / "LICENSE_COMMERCIAL.txt").write_text(
        """Cam Rig Builder — коммерческая / закрытая поставка

1. Исходный код пакета camrig поставляется в виде скомпилированного bytecode (.pyc).
   Декомпиляция и несанкционированное копирование логики запрещены правообладателем.

2. Файл tag_embedded.py поставляется в читаемом виде: он копируется в Python Tag сцены
   для работы без установленного плагина.

3. Точка входа cam_rig_builder.pyp — собственность правообладателя.

Контакт для лицензирования: <укажите контакт>.
""",
        encoding="utf-8",
    )

    (dst / "README_PRODUCTION.txt").write_text(
        """Cam Rig Builder — PRODUCTION сборка
Версия: %s

=== УСТАНОВКА ===
Скопируйте всю папку в каталог plugins Cinema 4D. Рядом должны быть:
  cam_rig_builder.pyp
  camrig/   (папка: __pycache__, __init__.py, tag_embedded.py, ud_template.json)
Перезапустите C4D. В Script Log: [CamRig] v… loaded

=== ИСПОЛЬЗОВАНИЕ ===
1) Extensions → Plugins → откройте «Cam Rig Builder» (или поиск по имени).
2) Create Rig — риг в корне документа. Если выделен null — риг встанет в его координаты.
3) Управление — User Data на объекте Cam_Rig: Orbit, Radius, Offset, повороты, камера,
   Shake, Target A/B, blend и т.д.
4) Reset — сброс групп или всего UD из диалога плагина.
5) Break User Data — «запечь» анимацию на объекты, удалить Python Tag; необратимо по смыслу рига.

Портируемые сцены: логика на Python Tag берётся из tag_embedded.py при создании рига.

=== ВАЖНО (Python / bytecode) ===
Bytecode собран интерпретатором: %s
Используйте ту же мажорную версию Python, что внутри вашей Cinema 4D, иначе импорт camrig может
не сработать. Пересоберите скриптом tools/build_production_release.py с ключом:
  --python "…\\python.exe из папки Cinema 4D\\…"

Ограничения защиты: .pyc не шифрование; см. LICENSE_COMMERCIAL.txt.

=== РЕЖИМ sources-only ===
Если сборка сделана с флагом --sources-only: в camrig/ лежат полные .py (без strip bytecode).
Подходит для любой версии Python в Cinema 4D; «защита» только организационная.
"""
        % (version, ("исходники, без bytecode" if sources_only else sys.version.split()[0])),
        encoding="utf-8",
    )

    (dst / ".gitignore").write_text(
        """__pycache__/
*.py[cod]
*.log
debug-*.log
""",
        encoding="utf-8",
    )


def _zip_folder(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        raise FileExistsError("Refusing to overwrite ZIP: %s" % zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                arc = f.relative_to(folder.parent)
                zf.write(f, arcname=str(arc))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Production bundle for Cam Rig Builder (bytecode по умолчанию или --sources-only)."
    )
    ap.add_argument("--out-root", type=Path, default=None, help="Каталог release (по умолчанию …/C4d_Plugins/release)")
    ap.add_argument("--keep-docs", action="store_true", help="Копировать папку docs/")
    ap.add_argument("--no-zip", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--development", action="store_true", help="Private sources-only bundle; no generated commercial license or public release.")
    ap.add_argument(
        "--sources-only",
        action="store_true",
        help="Не компилировать и не удалять .py — папка для любой версии Python в C4D",
    )
    ap.add_argument(
        "--python",
        type=Path,
        default=None,
        metavar="EXE",
        help="python.exe из установки Cinema 4D (рекомендуется для совместимости .pyc)",
    )
    args = ap.parse_args()
    if args.development:
        args.sources_only = True

    root = _plugin_root()
    version = _read_version(root)
    out_root = args.out_root or (root.parent.parent / "release")
    suffix = "development" if args.development else "production"
    dest = out_root / ("CamRig_%s_%s" % (version.replace(".", "_"), suffix))

    print("Source:", root)
    print("Dest:  ", dest)

    _copy_sources(root, dest, keep_docs=args.keep_docs)
    camrig_dst = dest / "camrig"
    py_exe = args.python
    if py_exe is not None and not py_exe.is_file():
        raise SystemExit("Python not found: %s" % py_exe)
    if not args.sources_only:
        if py_exe is None:
            guessed = _find_c4d_python_exe()
            if guessed is not None:
                print("Auto: compileall через python из Cinema 4D:", guessed)
                py_exe = guessed
        print("compileall via:", str(py_exe) if py_exe else sys.executable)
        _compile_bytecode(camrig_dst, py_exe)
        if py_exe is None and sys.version_info[:2] not in ((3, 10), (3, 11), (3, 12)):
            print(
                "WARNING: bytecode cpython-%d%d — проверьте совпадение с Python в Cinema 4D; "
                "при необходимости пересоберите с --python." % (sys.version_info[0], sys.version_info[1]),
                file=sys.stderr,
            )
        print("Removed .py:", [p.name for p in _strip_camrig_sources(camrig_dst)])
    else:
        print("Mode: sources-only (все .py сохранены, bytecode не требуется).")

    if args.development:
        (dest / "DEVELOPMENT_NOTICE.txt").write_text(
            "CamRig " + version + " private development build. Not a public release.\n"
            "The repository MIT LICENSE conflicts with the existing production builder's commercial text.\n"
            "No licensing decision has been made; do not distribute until the owner resolves it.\n"
            "See docs/ACCEPTANCE_1_5.md for verified scope and open HUD/manual acceptance items.\n",
            encoding="utf-8")
    else:
        _write_artifacts(dest, version, sources_only=args.sources_only)

    if not args.skip_verify:
        if args.sources_only:
            _verify_layout_sources_only(dest)
        else:
            _verify_layout(dest)

    if not args.no_zip:
        zp = out_root / ("CamRig_%s_%s.zip" % (version.replace(".", "_"), suffix))
        _zip_folder(dest, zp)
        print("ZIP:", zp)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
