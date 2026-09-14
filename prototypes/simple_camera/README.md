# Simple Camera — private working candidate

Independent from legacy CamRig. Core live checks pass; visual user acceptance and
Redshift motion-blur acceptance remain open. No plugin installation is required.

## Run in Cinema 4D

### Практический запуск

1. Откройте документ, в который нужно добавить новый риг. В Script Manager
   загрузите файл `create_simple_camera.py` из этой папки и выполните Execute.
   Скрипт добавляет отдельный Simple Camera и выделяет его корень; старые камеры
   остаются референсом. Документ автоматически не сохраняется.
2. В User Data корня откройте **Route / Body**. Поле **Path** показывает связанный
   сплайн: выберите объект Path в иерархии и редактируйте его точки. Сам сплайн
   не перемещайте и не масштабируйте; общий перенос/поворот задавайте корнем рига.
3. Поставьте ключи **Progress**: интерфейс показывает 0–100%, внутри хранится
   0–1. Раздвигайте ключи для замедления, делайте горизонтальный участок кривой
   для остановки. Редактируйте сплайн отдельно от времени прохождения маршрута.
4. **Height** задаёт высоту. В **Body Offset** ключуйте **Body Y** для прыжка,
   **Body X/Z** — для дополнительных смещений в осях рига. На время полёта
   опускайте **Walk → Strength** до нуля.
5. В **Look** включите **Use Target** и передвиньте связанный объект Target.
   **Pan / Tilt / Roll** добавляют поправку к наведению. Отключение Use Target
   включает ручной взгляд; этот переключатель не анимируется и не обещает
   сохранения кадрирования при смене режима.
6. В **Motion → Walk** настройте силу, длину шага, размах, наклоны и мягкость.
   Частота шага зависит от скорости маршрута и Step Length. **Shake / Drift**
   настраиваются отдельно; их сила по умолчанию равна нулю.
7. Для объектива выделите корень рига или любой его дочерний объект и выполните
   `select_camera.py` в Script Manager. Будет выделена единственная выходная
   камера: lens, exposure и DOF редактируются в её штатных настройках Redshift.
   Скрипт не переключает вид и не сохраняет сцену.

Поля **Path / Target / Camera** — справочные ссылки только для чтения, не входы
для замены источников. Поле **Status** предназначено для диагностики рига.
Позиции и углы можно вводить шире видимого диапазона слайдера; корректная длина
шага положительна, Softness находится между 0 и 1. На служебных объектах
Route / Aim / Look / FX / Camera не создавайте отдельные PSR-ключи.

### Исправление предпросмотра параметров с ключами

Слайдеры теперь показывают незаписанное изменение даже при наличии CTrack.
На остановленном кадре текущее значение User Data имеет приоритет для
предпросмотра. Для длины шага и частот незаписанное значение временно используется
как постоянное при расчёте фазы. Запись ключа сохраняет изменение; повторная
оценка анимации (например, при перемотке) возвращает значения из ключей, как в C4D.
Сами ключи риг не переписывает.

В уже созданной сцене выделите корень нового рига или его потомка и выполните
`update_selected_rig.py` из этой папки в Script Manager. Скрипт обновляет только
два известных Python-тега с Undo; неизвестный изменённый код он отвергает.
Новая сборка через `create_simple_camera.py` уже содержит исправление.

### Оптимизация отклика

Кэш геометрии зависит только от точек и касательных пути. История Walk зависит
от Progress и Step Length; Shake и Drift имеют отдельные интегралы частоты.
Повороты, Body offsets, сила и размах эффектов не сбрасывают эти интегралы.
Постоянные частоты считаются напрямую. Постоянная длина шага использует кэш
пройденного расстояния — его не нужно перестраивать на каждом движении слайдера.

Сравнение с предыдущим пакетом на одном риге, кадр150: медиана обработки Pan,
Body Y, силы/размаха Walk, Step Length и Shake Frequency снизилась с117–126ms
до0.9–1.2ms; Progress с117ms до6.8ms. Это host evaluation без отрисовки viewport.
56 сравнений значений слайдеров сохранили матрицы в пределах1e-5; максимальная
наблюдённая разница1.6e-12. Evidence: optimization_v001/evidence.json.
Перемотка/save-reopen: python_v007; редактирование/Undo/two-rig: edit_v003;
keyed live preview: live_edit_v002. Все PASS.

### Запуск для разработчика

On the main thread, load `builder.py` with `runpy.run_path()` and call `fixture()`.
It returns `(owned_detached_document, root, role_objects, control_descids)`.
No user document is read, replaced or activated. `build(document)` inserts one
new rig into the explicitly supplied document with an Undo record.

Builder embeds `motion_math.py`, `path_math.py`, `curve_math.py`, `runtime.py` into
two Python tags. Saved scenes therefore have no dependency on these source files.
The native camera owns its lens settings. Root controls are grouped into
Route / Body, Look, Motion (Walk / Shake / Drift), and Camera. Creation and camera
selection scripts expose `main(document=None)` for explicitly owned test documents;
normal `runpy.run_path()` loading does not execute them.

## Implemented

- Static open Bezier arc mapping to native Align parameter; Tangential disabled.
- Rig-up height and keyed Body jump offset before native Target.
- Manual Target enable state and explicit Pan/Tilt/Roll composition.
- Procedural Walk, seeded Shake and Drift, phase evaluated from fixed time origin.
- Prefix integration cache which can be rebuilt independently of visited frames.
- One Redshift camera; no imports from old CamRig, no Motion Camera/Footsteps.

## Current evidence

25 pure tests pass with bundled C4D Python. Live 181-frame fixture with eased
Progress and animated Step Length / Shake Frequency passes repeat, mixed order,
reverse, fresh-frame, subframe and save/reopen checks (matrix component differences
below 1e-15; no tag diagnostics). Evidence and portable scene:
`tests/artifacts/simple_camera/python_v005/evidence.json` and `simple_camera.c4d`.
Independent 20000-segment
route reference gives max sampled position error 0.000146 cm. Body offset stays
rig-up with Tilt70/Roll90; height170 + jump100 produces (0,270,0).

Additional live evidence under `tests/artifacts/simple_camera/`:

- `edit_v002/edit_evidence.json`: six input edits, builder Undo/Redo and two-rig
  isolation PASS; warmed edited results match independently created fixtures.
- `controls_v003/evidence.json`: 15 checks PASS, including commands, grouped UI
  metadata, both manual/target transitions in the same pass, zero FX identity,
  jump basis and unchanged native camera data / source keys.
- `numerical_v001/numerical_evidence.json`: 120 vs480 Hz refinement difference
  <0.000185 cm / <5.52e-7 basis component. Five invalid-source guards PASS.
  One/six rigs: ~1.74/10.21 ms per warm frame; cold seek to frame180 ~132/769 ms.
  These six-second fixtures measure evaluation without rendering.
- `passage_v003/simple_camera_passage.c4d` and `preview.mp4`: editable passage with
  stop, pan and jump. Viewport preview samples motion at10 Hz, packaged at30fps;
  it does not demonstrate Redshift motion blur.

These are bounded checks, not proof for arbitrary external driver graphs or all
animation durations. V1 supports a static top-level rigid root at scale1 and a
static open Bezier path; directly key root controls and the Target. Do not key
mode, deform the path, add expression dependencies, or key driven PSR channels.
Integration is capped at1000 seconds from document start. Diagnostics appear in
Status; invalid input retains the last output and must be corrected before use.

To review: open the passage .c4d, play frames0–180, then adjust Walk/Shake/Drift
and the look. User approval of motion and a production Redshift motion-blur check
are separate remaining gates. Legacy CamRig and its scenes were not changed.

Pure checks:
`<bundled C4D Python> -m unittest discover -s prototypes/simple_camera -p test_*.py`

Extended live `acceptance.py` requires a fresh output directory and writes the
portable .c4d and JSON evidence. Binary outputs belong in ignored
`tests/artifacts/simple_camera/`. Always inspect tag diagnostics in tests; a
returned camera transform alone is not success.

## Reuse provenance

UD creation and expression-priority idioms are locally adapted from old CamRig
`ud_build.py` / `scene_support.py`, previously located with Serena. The pure arc
mapper, deterministic value noise and gait functions are new independent modules.
No third-party source copied. The former native experiment is preserved under
`experiments/native_walk/` as failure evidence.
