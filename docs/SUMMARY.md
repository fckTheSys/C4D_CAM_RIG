# CamRig 1.6.0 — текущее поведение

Источники истины: config.py, ud_template.json, tag_embedded.py и тесты. Формат рига: schema 3; отсутствие маркера означает legacy. [Параметры](UDref.md), [Upgrade](UPGRADE_1_5.md), [Follow Spring](SPRING_1_6.md), [приёмка](ACCEPTANCE_1_6.md).

## Структура

Иерархия 1.4 сохранена: корень с Target_A, Target_B, Look_Target и кругом Main_Camera; под кругом Follow → Offset → Spring_Offset → RS_CAM → FX_CAM → Focus. Камеры могут быть standard или Redshift. Промежуточный legacy Inertia_Follow разрешается, но старый объект автоматически не переиспользуется.

На корне находятся 37 контрола в девяти группах. Внешние ссылки не сбрасываются Reset All. Трансформация корня не меняется командами Reset.

## Вычисление

Три стадии содержат полный автономный tag_embedded.py без импорта camrig и чтения файлов. Роль хранится в metadata тега (namespace 1244567, поле 10): 1 — Runtime, 2 — Spring, 3 — Focus. Переименование тега не меняет его роль.

| Стадия | Expression priority | Назначение |
|---|---:|---|
| CamRig Runtime 1.5 | -20 | Разрешение объектов, UD, плоскость/фаза, Offset/Rotation, focal, Shake/Drift, смешивание целей и Aim Offset |
| Align to Spline | -10 | Положение и направление Follow |
| CamRig Spring 1.6 | -5 | Воспроизводимая позиционная инерция до Target |
| Target Expression | 0 | Ориентация основной камеры |
| CamRig Focus 1.5 | 20 | Фокус по итоговой матрице FX-камеры |

Orbit хранит градусы без ограничения числа оборотов. Только spline phase получает (Orbit % 360) / 360. Значения UD и ключи не переписываются. Radius ограничен снизу нулём; soft slider не является пределом допустимого значения.

Центр внешнего Orbit Center преобразуется из world в root local; далее прибавляются Center X / Height / Center Z. Вращение и масштаб внешней цели не наследуются. HPB круга применяется вокруг его центра. Внутренние Target_A/B не перемещаются вслед за Height и Plane Tilt.

Follow Spring использует Spring Amount, Spring Response и Spring Damping. Solver работает на фиксированной сетке 120 Hz, аналитически решает мировые координаты и хранит кэш только в экземпляре runtime-тега. Amount 0 полностью отключает расчёт и оставляет Spring_Offset нулевым. Подробности и ограничения источников описаны в [SPRING_1_6.md](SPRING_1_6.md).

Aim Offset задаётся в координатах корня и добавляется к смешанной мировой точке A/B. Focus Mode Manual использует Focus Distance; Look Target — итоговую точку взгляда при включённом targeting; Focus Target — отдельную ссылку. Для автофокуса используется проекция на оптическую ось FX плюс Focus Offset, минимум 1. При недействительной цели используется ручная дистанция. DOF и диафрагма не включаются автоматически.

Прямые ссылки на управляемую ветвь камеры и Look_Target не используются; Inspector объясняет отказ. Общий анализ циклов через чужие XPresso/constraints не реализован.

## Команды

Select Rig/Orbit/Targets и Look Through Camera разрешают риг по выделению. Если кандидатов несколько, диалог предлагает выбор; программные вызовы без интерактива возвращают ошибку неоднозначности.

Upgrade — явная миграция известного legacy runtime. Repair восстанавливает отсутствующие компоненты известных schema-3 ригов и их приоритеты, не подменяет пользовательский код. Schema 2 сначала требует Upgrade. Структурных удалений из expression нет.

Break не является Bake Camera. Он блокирует новые значения/анимацию Orbit Rig, Aim Offset, автофокус и новые ссылки, а также любой анимированный Orbit и значения вне одного оборота. Полный bake остаётся отдельной задачей.

HUD Show/Hide не реализованы; нативный HUD можно настроить вручную через Add to HUD в Attribute Manager. Никакие чужие HUD-элементы не изменяются.

## Модули

- rig_builder.py — сохранённый публичный фасад.
- rig_assemble.py — сборка иерархии, тегов, слоёв, UD.
- commands.py — выбор/навигация, preflight и Upgrade, защита Break.
- scene_support.py — schema metadata, приоритеты и Undo.
- ud_build.py / ud_template.json — UI-схема, числовые границы отдельно от slider.
- tag_embedded.py — автономные runtime, sampler и математические функции; spring.py — host-side sampler/cache reference.
- rig_reset.py / rig_break.py — Reset и ограниченный перенос старых контролов.
- diagnostics.py — Inspector и Repair.
- tests/test_spring_math.py — независимые solver-тесты; tests/c4d_acceptance.py — сценарии в настоящем C4D; tools/check_project.py — статические проверки.

Исторические Interaction, Technical Specification и deep-research-report не описывают гарантированные текущие возможности. Spline Position, Speed Offset, presets, arbitrary spline, spherical orbit, вращательная инерция и gizmo-контрол плоскости не реализованы.
