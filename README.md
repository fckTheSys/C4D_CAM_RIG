# C4D Cam Rig (Cam Rig Builder)

**Cinema 4D** · Python command plugin · **v1.4.0** (см. `camrig/config.py`)

Краткое описание для GitHub *About*:  
*Orbital camera rig for Cinema 4D: User Data control, embedded Python Tag for portable scenes, reset and bake (Break).*

---

## Ключевые возможности

- **Орбитальный камерный риг** — сплайн-круг (Main_Camera), Align to Spline, Target Expression, две камеры (RS/стандарт + FX для shake/rotation).
- **Управление через User Data** на корне `Cam_Rig`: орбита, радиус, offset, поворот, focal, focus distance, shake, target A/B, blend, free camera.
- **Портируемые сцены** — в Python Tag встраивается полный код из `camrig/tag_embedded.py`; сцена открывается и работает **без установленного плагина** (логика на теге).
- **Сброс по группам** и **Reset All** из диалога плагина.
- **Break User Data** — перенос анимации с UD на объекты, снятие слоёв, удаление Python Tag (риг «запекается» в ключи).
- **Rig Inspector / Repair / Self check** (диалог) — диагностика выбранного рига и точечный ремонт.
- **Camera Drift** (опционально) — медленный дрейф в группе Shake (`Drift Pos`, `Drift Rot`, `Drift Frequency`); по умолчанию не меняет прежнее поведение.
- **Legacy** — старые сцены с промежуточным null `Inertia_Follow` между Follow и Offset по-прежнему распознаются (инерция не считается).

Подробная архитектура и таблицы UD: **[docs/SUMMARY.md](docs/SUMMARY.md)**, **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Требования

- **Cinema 4D** с поддержкой **Python** (плагин `.pyp` + пакет `camrig/`).
- Для **Redshift Camera** при сборке рига — установленный Redshift (иначе подставляется стандартная `Ocamera`).

---

## Установка (кратко)

1. Склонируй репозиторий или скачай ZIP.
2. Скопируй **всю папку** `C4D_CAM_RIG` (или переименуй в `CamRig`) в каталог плагинов C4D, например:
   - Windows: `%USERPROFILE%\Documents\MAXON\Cinema 4D RXX_XXXXXX\plugins\`
   - Внутри должны лежать рядом: `cam_rig_builder.pyp` и папка `camrig\`.
3. Перезапусти Cinema 4D.
4. В **Script Log** при успешной загрузке: `[CamRig] v1.4.0 loaded`.

Полная пошаговая инструкция: **[INSTALL.md](INSTALL.md)**.

---

## Использование (кратко)

1. **Extensions → Plugins** (или поиск в Command Palette) — команда **Cam Rig Builder**.
2. **Create Rig** — риг в корне документа; если выбран null — позиция/ориентация из его глобальной матрицы.
3. Параметры — в **Attribute Manager** на объекте **Cam_Rig** (User Data).
4. **Reset** / **Break User Data** — кнопки в диалоге плагина (для Break удобно выделить объект внутри рига).

---

## Структура репозитория

| Путь | Назначение |
|------|------------|
| `cam_rig_builder.pyp` | Точка входа: команда, диалог, регистрация CamRigRoot |
| `camrig/` | Пакет: сборка рига, UD, reset/break, встроенный рантайм |
| `camrig/tag_embedded.py` | Код Python Tag (синхронизировать версию с `config.PLUGIN_VERSION`) |
| `docs/` | Документация (SUMMARY, ARCHITECTURE, ROADMAP, …) |

---

## Важно для разработчиков

- Перед релизом: **`EMBEDDED_RUNTIME_VERSION`** в `tag_embedded.py` = **`PLUGIN_VERSION`** в `config.py` (плагин предупреждает при рассинхроне).
- Для распространения замените **Plugin ID** в `camrig/config.py` на выданные в [PluginCafe](https://developers.maxon.net/).

---

## Публикация на GitHub

См. **[GITHUB.md](GITHUB.md)**.

---

## Лицензия

Укажите свою лицензию в репозитории (файл `LICENSE`). Исходный код предоставляется как есть, без гарантий.
