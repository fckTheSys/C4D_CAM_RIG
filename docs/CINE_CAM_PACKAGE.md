# Camera Rigs 0.5.2 — релиз документации

Добавлен единый [практический гид](CAMERA_RIGS_GUIDE_RU.md): назначение четырёх
режимов, эффект каждого параметра, все кнопки панели, защита ключей, Redshift и
границы переносимости. Runtime и данные сцен не изменены.

Пять нативных групп панели: Create rig, Selected rig, Viewport, Tools, Reset.
Кнопки стандартной высоты, создание четырёх ригов в одной строке.

ZIP: `release/private/Camera_Rigs-0.5.2.zip` (14 файлов).
SHA-256: `614c872a7597ba4040a25be82b167aea6917487269972e300eda42df7637f2d2`.
Установленная копия обновлена с проверкой manifest; предыдущая копия сохранена
в `release/private/Cine_CAM-backup-6174e86d62134b7bbada0505d6fee900`.

## Архив: Camera Rigs 0.5.1 — компактная панель

Обновлено 2026-09-16. Актуальная версия пакета — **0.5.6**. Общая панель содержит Orbit, Trajectory, Free и CK_CAM POV.
Команда после обычного запуска: **Camera Rigs (Cine + CK_CAM)**, ID 10699230.
Папка установки остаётся `Cine_CAM`. Отдельный старый CK_CAM и legacy сохранены.
Redshift для CK_CAM оставлен по решению пользователя.

В 0.5.6 CK_CAM использует `Full Walk Speed` для настройки выразительности
медленной ходьбы. Новые World/Local Target создаются цветными Null-маркерами
с формами Sphere/Triangle и нативным Radius. Обновляются только новые риги;
существующие сцены не мигрируют автоматически.

Панель: сетка 2×2 для создания, выбранный риг, навигация, просмотр через камеру,
инспектор/справка и отдельный блок сбросов. Без выделенного рига инструменты серые.
Это доступность кнопок меню, а не изменение нативной панели User Data.

Проверены в C4D исходная и установленная копии: четыре создания, навигация,
инспектор, сбросы, отказ сброса анимированных контроллеров до записи.
Внешний вид проверен по снимку самого окна. Установленная панель открыта живьём.
Регистрация команды при следующем запуске ещё не проверена.
[Проверка автономности CK_CAM](CK_CAM_PORTABILITY.md): save/reload и изоляция imports,
11 смешанных/дробных кадров; другой компьютер и рендер-ферма остаются отдельной проверкой.

ZIP: `release/private/Camera_Rigs-0.5.0.zip` (14 файлов).
SHA256: `5e4fd574054989321820b83ea98a5935348adfdaf879870be5680635540c3c4b`.
Обновление сверило старый manifest и сохранило резервную копию:
`release/private/Cine_CAM-backup-3897d1abad794b8d89333f65499b3a1c`.
Для повторной сборки используй новое имя ZIP и `--update-existing` при обновлении
известной установки; изменённые файлы прежнего manifest вызывают отказ.

---

## Архив: пакет 0.4.0

# Cine Camera — package 0.4.0

Private development plugin, command ID 10699230. Menu style follows the old
CamRig command palette; the new plugin does not import CamRig or CK_CAM.
Universal P3 remains frozen legacy. No repository commit or push is part of this package.

Sources: [Cine_CAM](../Cine_CAM/README.md), [fixed variants](../prototypes/cine_variants/README.md).

## Menu decisions

| Old command | New package |
| --- | --- |
| Create Rig | Three explicit buttons: Orbit / Trajectory / Free |
| Select Rig / Orbit / Targets / Look Through | Rig / Motion Controller / Target / Camera / Look Through |
| Inspector | Read-only structural/header/link check and current runtime status |
| Many reset buttons | Reset Framing and Disable Effects; preflight rejects keyed controls |
| Upgrade / Repair | Omitted: frozen legacy and fixed new schema, no migration |
| Break User Data | Omitted: not a full camera bake |
| Reset All | Omitted: unnecessarily broad action |
| Self check | Development acceptance scripts; not a scene-writing action in the artist menu |

Future useful addition: full camera bake, separately implemented and accepted.
No placeholder/nonfunctional bake button is included.

## Build and installed evidence

Command from repository root, with bundled C4D Python:

```text
tools/package_cine_cam.py --output release/private/Cine_CAM-0.4.0.zip --plugins-dir <C4D user plugins directory>
```

The builder refuses existing output/install paths. Explicit allowlist: pyp entry,
menu, README, four runtime sources, manifest. No scenes, credentials, dependencies,
legacy sources or local tool configuration. The ZIP and installed files are hash-checked.

15.09.2026 results:

- ZIP: `release/private/Cine_CAM-0.4.0.zip`, 8 files.
- ZIP SHA-256: `9a1675bd14be59943ec645d44ef65765edcd19bfbf99790780a4692c7f08ef22`.
- Installed in user `plugins/Cine_CAM` without changing existing plugins.
- `acceptance_menu.py` PASS against development and installed menu paths:
  three creation actions, navigation from descendants, inspector, resets, keyed
  reset refusal before writes. Tests use their own C4D document.
- The installed GeDialog palette was opened in the existing session. Actual
  command registration/loading at C4D startup remains unverified until next launch.
- Fixed-variant movement/effects and native save/load comparison passed earlier.
  Actual farm and Redshift motion blur remain unverified.

The plugin is needed only on the creation workstation. It adds no custom scene
objects or external runtime imports. The saved camera rigs contain their Python
Tags; compatible C4D/Python execution and the chosen renderer are still required.
