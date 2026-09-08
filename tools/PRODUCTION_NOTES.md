# Production-сборка Cam Rig Builder

## Суть

- Пакет `camrig` компилируется в **bytecode** (`python -OO -m compileall`), исходники `.py` удаляются.
- Исключения: **`tag_embedded.py`** (читается с диска при сборке Python Tag) и **`__init__.py`** (маркер пакета; без него `import camrig` часто ломается).
- **`--sources-only`**: копия без `compileall`/strip — все `.py` в `camrig/`; подходит для любой версии Python в C4D (без «защиты» bytecode).
- Если **`--python` не задан** (и не `--sources-only`), на Windows скрипт пробует найти `python.exe` в типичных путях `Maxon Cinema 4D 20xx\resource\modules\python\libs\`.
- **`cam_rig_builder.pyp`** остаётся текстом (точка входа C4D).

## Запуск

```powershell
cd …\active\CamRig

$py = "C:\Program Files\Maxon Cinema 4D 2026\resource\modules\python\libs\python311\python.exe"
& $py tools\build_production_release.py --python $py

# Или системный Python (может не совпасть с C4D — лучше явный --python или авто-поиск C4D):
python tools\build_production_release.py

# Только копия с полными .py (без bytecode):
python tools\build_production_release.py --sources-only --no-zip
```

Артефакты: **`…/C4d_Plugins/release/CamRig_<версия>_production/`** и **`.zip`**.

## Ограничения

- Bytecode **не** равно шифрование; возможна декомпиляция.
- **`tag_embedded.py`** и **`.pyp`** остаются читаемыми по необходимости архитектуры.
- В исходниках добавлен `Init(..., isCloneInit)` для совместимости с C4D 2024+ / 2025.
