# CamRig — подробное саммари

Версия плагина в коде: `camrig/config.py` (`PLUGIN_VERSION`, `PLUGIN_SLUG`). Для этого проекта источником версии является `camrig/config.py`; общей workspace-таблицы версий в текущем checkout нет.

## 1. Назначение

Cam Rig Builder — плагин Cinema 4D для создания **орбитального** камерного рига. Риг управляется через **User Data** на объекте **Cam_Rig**: орбита, offset, focal, target, shake. Python Tag на **Main_Camera** каждый кадр читает UD и применяет их к объектам.

**Не входит в продукт:** Motion Camera rig (Tmotioncam), инерция камеры и UD «Inertia». Старые сцены с `Motion_Cam_Rig` или встроенным слоем инерции плагин не мигрирует; орбитальный риг по-прежнему можно открыть, если иерархия совместима (см. ниже про legacy `Inertia_Follow`).

---

## 2. Архитектура

Схема модулей и граница с **`tag_embedded.py`**: **[`ARCHITECTURE.md`](ARCHITECTURE.md)**.

| Файл | Роль |
|------|------|
| `camrig/config.py` | Константы, имена UD, дефолты, ID плагинов, `DEBUG_LOG` |
| `camrig/rig_builder.py` | Фасад: реэкспорт `build_cam_rig`, Reset/Break, примитивов UD, `validate_ud_template_vs_config` |
| `camrig/rig_assemble.py` | Сборка иерархии рига и Python Tag из `tag_embedded.py` |
| `camrig/ud_build.py` | Примитивы UD, загрузка `ud_template.json`, валидация совпадения с `UD_DEFAULTS` при старте |
| `camrig/rig_reset.py` / `rig_break.py` | Сброс UD и Break (перенос треков) |
| `camrig/ud_utils.py`, `log.py`, `user_data.py` | Общие хелперы |
| `camrig/tag_embedded.py` | **Единственная логика рантайма** для портируемых сцен: тот же код копируется в `TPYTHON_CODE`. `EMBEDDED_RUNTIME_VERSION` = `PLUGIN_VERSION` |
| `camrig/python_tag_logic.py` | Тонкая обёртка: вызывает `tag_embedded` при установленном плагине |
| `camrig/rig_objects.py` | Разрешение объектов для Break (`get_rig_objects`) |
| `camrig/ud_template.json` | Группы UD: Orbit, Transform, Camera, Shake, Target |
| `cam_rig_builder.pyp` | Командный плагин (диалог), CamRigRoot ObjectData |

**Поток данных:** User Data (Cam_Rig) → Python Tag → чтение UD → применение к circle, align, offset, cam, fx, look_target, focus.

---

## 3. Иерархия рига (текущая сборка)

```
Cam_Rig              ← корень (CamRigRoot или Onull)
├── Target_A
├── Target_B
├── Look_Target
└── Main_Camera      ← Osplinecircle, Python Tag (полный tag_embedded.py)
    └── Follow       ← null + Align to Spline (орбита по circle)
        └── Offset   ← null (XYZ из UD); прямой потомок Follow
            └── RS_CAM        ← Target Expression → Look_Target
                └── FX_CAM    ← Rot H/P/B, Shake
                    └── Focus ← null (Focus Distance)
```

**Legacy:** в старых сценах между Follow и Offset мог оставаться null с именем, начинающимся с `Inertia_Follow`. Рантайм и `get_rig_objects` по-прежнему находят Offset как потомка этого null, но инерция не вычисляется.

---

## 4. User Data (на Cam_Rig)

| Группа | Параметры | Куда применяется |
|--------|-----------|------------------|
| Orbit | Orbit, Radius | Align Position; радиус circle |
| Transform | Offset X/Y/Z, Rot H/P/B | Offset; вращение FX_CAM |
| Camera | Focal Length, Focus Distance | Обе камеры; Focus |
| Shake | Enable, Pos, Rot, Drift Pos, Drift Rot, Drift Frequency | Процедурный noise и медленный drift на FX_CAM |
| Target | Use Target, Target A/B, Blend, Free Camera | Target Expression; позиция Look_Target |

---

## 5. Python Tag (каждый кадр)

Реализация — в `tag_embedded.py` (идентично встроенному коду в сцене).

1. `get_rig_objects(circle)` — см. `rig_objects.py` / зеркало в embedded.
2. `_read_all_user_data(rig)` (fallback: circle).
3. Применение orbit, offset, focal, focus, shake, target.

---

## 6. Break User Data

Как раньше: перенос анимированных UD на объекты, снятие слоёв, удаление Python Tag с Main_Camera. См. `rig_builder.break_rig_user_data`.

---

## 7. Диалог плагина

- **Create Rig** — орбитальный риг в корне документа (или в позиции выбранного null / CamRigRoot).
- **Break User Data**
- **Reset** — группы orbit, transform, camera, target, shake; Reset All.
- **Rig Inspector** — проверка иерархии, тегов и embedded runtime.
- **Repair Selected Rig** — безопасное восстановление Align tag, Target tag, Focus и Python Tag, если они отсутствуют.

---

## 8. Версионирование

При изменении логики обновляйте **`PLUGIN_VERSION`** в `config.py`, **`EMBEDDED_RUNTIME_VERSION`** в `tag_embedded.py` и запись в корневом **`CHANGELOG.md`**.
