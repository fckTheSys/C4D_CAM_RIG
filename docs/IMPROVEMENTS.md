# Предложения по улучшению структуры CamRig

## 1. Разрешение объектов рига — сделано

Общая логика в [`rig_objects.py`](../camrig/rig_objects.py); Break использует её через [`rig_break.py`](../camrig/rig_break.py). В портируемой сцене дубликат логики остаётся в [`tag_embedded.py`](../camrig/tag_embedded.py) — см. [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 2. Отладочный вывод и лог

**Сейчас:** Флаг `DEBUG_LOG` в [`config.py`](../camrig/config.py); [`log.py`](../camrig/log.py) — префикс `[CamRig]` для Script Log.

**Исторически:** При необходимости файлового `_debug_log` завязать на `DEBUG_LOG`.

---

## 3. Разбить монолитный rig_builder — сделано

Сборка: [`rig_assemble.py`](../camrig/rig_assemble.py), UD: [`ud_build.py`](../camrig/ud_build.py), Reset/Break: [`rig_reset.py`](../camrig/rig_reset.py), [`rig_break.py`](../camrig/rig_break.py); [`rig_builder.py`](../camrig/rig_builder.py) — фасад.

---

## 4. Единый источник имён User Data

**Сейчас:** Имена по-прежнему в `config.py` и строками в `ud_template.json`.

**Сделано:** При загрузке плагина [`validate_ud_template_vs_config()`](../camrig/ud_build.py) проверяет двунаправленно: все `real`/`bool` из JSON есть в `config.UD_DEFAULTS`, и все ключи `config.UD_DEFAULTS` представлены в JSON. Несоответствия пишутся как WARNING в Script Log.

**Дальше (по желанию):** генерация JSON из config или скрипт parity без C4D.

---

## 5. Типизация и контракты

**Сейчас:** Общий `RigObjects` в [`rig_objects.py`](../camrig/rig_objects.py).

**Дальше:** Расширить type hints публичных функций фасада при желании.

---

## 6. Логирование и диагностика — сделано

[`camrig/log.py`](../camrig/log.py) (`info` / `warn` / `error`). Все runtime-сообщения в пакете идут через единый префикс `[CamRig]`: [`rig_objects.py`](../camrig/rig_objects.py), [`rig_assemble.py`](../camrig/rig_assemble.py), [`rig_break.py`](../camrig/rig_break.py), [`ud_build.py`](../camrig/ud_build.py). В [`cam_rig_builder.pyp`](../cam_rig_builder.pyp) сохранены локальные `_log_*` (нужны до момента успешного импорта пакета).

---

## 7. Документация и версии

Есть [`CHANGELOG.md`](../../CHANGELOG.md) в `active/`, [`ARCHITECTURE.md`](ARCHITECTURE.md). Дальше — раздел «Обратная совместимость» в SUMMARY для редких старых сцен при необходимости.

---

## 8. Структура каталогов

**Сейчас:** `camrig/` (пакет), `docs/`, корень с `cam_rig_builder.pyp`.

**Предложение:** Оставить как есть; при появлении тестов — папка `tests/` в корне. Утилитные скрипты (например генерация UD из config) — в `scripts/` или в `docs/` с пояснением. Файлы логов `debug-*.log` добавить в `.gitignore`, чтобы не коммитить.

---

## 9. Конфиг и константы отображения

**Сейчас:** Радиус, цвет, режим отображения и usecolor для Focus задаются в `config` (`FOCUS_*`).

---

## 10. Приоритет дальнейших работ

- **По желанию:** константы отображения Focus уже частично в config — дополнить при необходимости (п.9).
- **Низкий приоритет:** `tests/` или скрипт проверки parity embedded ↔ config (п.8).
