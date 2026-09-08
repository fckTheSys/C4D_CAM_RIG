# CamRig 1.6 — User Data reference

Все параметры находятся на корне **Cam_Rig**, не на Main_Camera. Таблица сверена с ud_template.json. Угловые значения — обычные числа в градусах; их числовая семантика не меняется на радианы.

Hard limits ограничивают ввод, slider range — только удобный диапазон ползунка. «Без границ» означает конечное число типа REAL, не поддержку NaN/Infinity.

| Группа | Постоянный ключ | Параметр | Тип | По умолчанию | Hard limits | Slider |
|---|---|---|---|---|---|---|
| Orbit | `orbit` | Orbit | real | 0 | −∞ … +∞ | 0 … 360 |
| Orbit | `radius` | Radius | real | 500 | 0 … +∞ | 0 … 5000 |
| Transform | `offset_x` | Offset X | real | 0 | -2000 … 2000 | -2000 … 2000 |
| Transform | `offset_y` | Offset Y | real | 0 | -2000 … 2000 | -2000 … 2000 |
| Transform | `offset_z` | Offset Z | real | 0 | -2000 … 2000 | -2000 … 2000 |
| Transform | `rot_h` | Rot H | real | 0 | -180 … 180 | — |
| Transform | `rot_p` | Rot P | real | 0 | -180 … 180 | — |
| Transform | `rot_b` | Rot B | real | 0 | -180 … 180 | — |
| Camera | `focal_length` | Focal Length | real | 36 | 10 … 200 | 10 … 200 |
| Camera | `focus_distance` | Focus Distance | real | 1000 | 1 … 100000 | 1 … 100000 |
| Shake | `shake_enable` | Shake Enable | bool | false | — | — |
| Shake | `shake_pos` | Shake Pos | real | 5 | 0 … 100 | 0 … 100 |
| Shake | `shake_rot` | Shake Rot | real | 1 | 0 … 20 | 0 … 20 |
| Shake | `drift_pos` | Drift Pos | real | 0 | 0 … 50 | 0 … 50 |
| Shake | `drift_rot` | Drift Rot | real | 0 | 0 … 10 | 0 … 10 |
| Shake | `drift_frequency` | Drift Frequency | real | 0.08 | 0.01 … 1 | 0.01 … 1 |
| Target | `use_target` | Use Target | bool | true | — | — |
| Target | `target_a` | Target A | link | target_a | — | — |
| Target | `target_b` | Target B | link | target_b | — | — |
| Target | `target_blend` | Target Blend | real | 0 | 0 … 100 | 0 … 100 |
| Target | `free_camera` | Free Camera | bool | false | — | — |
| Orbit Rig | `center_x` | Center X | real | 0 | −∞ … +∞ | -2000 … 2000 |
| Orbit Rig | `height` | Height | real | 0 | −∞ … +∞ | -2000 … 2000 |
| Orbit Rig | `center_z` | Center Z | real | 0 | −∞ … +∞ | -2000 … 2000 |
| Orbit Rig | `plane_h` | Plane Heading | real | 0 | −∞ … +∞ | -180 … 180 |
| Orbit Rig | `plane_p` | Plane Tilt | real | 0 | −∞ … +∞ | -180 … 180 |
| Orbit Rig | `plane_b` | Plane Bank | real | 0 | −∞ … +∞ | -180 … 180 |
| Orbit Rig | `orbit_center` | Orbit Center | link | пусто | — | — |
| Aim Offset | `aim_x` | Aim Offset X | real | 0 | −∞ … +∞ | — |
| Aim Offset | `aim_y` | Aim Offset Y | real | 0 | −∞ … +∞ | — |
| Aim Offset | `aim_z` | Aim Offset Z | real | 0 | −∞ … +∞ | — |
| Focus | `focus_mode` | Focus Mode | enum | Manual | Manual / Look Target / Focus Target | — |
| Focus | `focus_target` | Focus Target | link | пусто | — | — |
| Focus | `focus_offset` | Focus Offset | real | 0 | −∞ … +∞ | — |
| Spring | `spring_amount` | Spring Amount | real | 0 | 0 … 100 | 0 … 100 |
| Spring | `spring_response` | Spring Response | real | 60 | 0 … 100 | 0 … 100 |
| Spring | `spring_damping` | Spring Damping | real | 65 | 0 … 100 | 0 … 100 |

## Практическое поведение

- Orbit 0 → 1080 — три прямых оборота; 0 → −720 — два обратных. При нескольких оборотах используйте числовой ввод и F-Curve, не только slider.
- Center X / Height / Center Z перемещают круг в координатах корня, а не внутренние Target A/B. Plane Heading/Tilt/Bank вращают круг вокруг его центра.
- Orbit Center наследует только мировую позицию внешнего объекта. Масштаб и вращение этой цели игнорируются.
- Aim Offset X/Y/Z добавляется после Target Blend в координатах корня.
- Manual оставляет ручной Focus Distance. Look Target работает при Use Target и выключенном Free Camera; иначе manual. Focus Target при пустой/недействительной ссылке также использует manual.
- Автофокус = глубина точки вдоль оси итоговой FX-камеры + Focus Offset, минимум 1. DOF/диафрагма не включаются.
- Reset All сохраняет все ссылки и трансформацию корня. Ключи не удаляет: следующий animation evaluation снова применит F-Curve.
- Прямые циклические ссылки игнорируются runtime; Inspector объясняет причину. Сама пользовательская ссылка не стирается.
- Spring Amount смешивает обычную и инерционную позицию; Response задаёт 0.5–5 Hz, Damping — коэффициент 0.2–1.0. Spring действует до Target и не пружинит Shake/Drift.

## Не реализовано

Spline Position, Speed Offset, движение по произвольному сплайну, spherical orbit, presets, rotational inertia и управление кругом gizmo не являются контролами 1.6.

Show/Hide Rig HUD пока отсутствуют. Нативный HUD можно создать вручную: выделить нужные User Data в Attribute Manager → контекстное меню Add to HUD. Рекомендуемый набор: Orbit, Radius, Height, Plane Tilt, Focal Length. Это исходные UD, не копии; работу через HUD ещё нужно принять вручную. [Ограничение Python SDK](https://developers.maxon.net/forum/topic/14678/python-script-is-add-to-hud-possible-to-add-to-my-python-script).

[Follow Spring](SPRING_1_6.md) · [Upgrade](UPGRADE_1_5.md) · [Проверки](ACCEPTANCE_1_6.md)
