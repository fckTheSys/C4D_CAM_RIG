# Changelog — C4D Cam Rig

## 1.4.0 (2026-05-08)

- Добавлены Rig Inspector, Repair Selected Rig и Self check в диалог.
- Добавлен низкорисковый Camera Drift: новые UD `Drift Pos`, `Drift Rot`, `Drift Frequency` в группе Shake; дефолты не меняют старое поведение.
- `EMBEDDED_RUNTIME_VERSION` синхронизирован с `PLUGIN_VERSION`.

## 1.3.1 (2026-05-08)

- Модульная структура: `ud_build`, `rig_assemble`, `rig_reset`, `rig_break`; фасад `rig_builder.py`.
- `ud_utils.py`, `log.py`; двунаправленная валидация `ud_template.json` ↔ `UD_DEFAULTS` при загрузке.
- Сообщения в пакете через `camrig.log`; публичный `add_group` в UD-сборке.

## 1.3.0 (2026-05-08)

- Удалены Motion Camera rig и Inertia из продукта; только орбитальный риг.
- Упрощена иерархия Follow → Offset; legacy `Inertia_Follow` распознаётся в старых сценах.
