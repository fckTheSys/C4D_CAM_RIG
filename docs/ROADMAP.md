# CamRig Roadmap — будущие улучшения

Текущее ядро поставки: **орбитальный риг** — Orbit, Transform, Camera, Shake, Target. Код рантайма сосредоточен в `camrig/tag_embedded.py` (копируется в Python Tag).

**Удалено в 1.3.0:** Motion Camera rig, User Data и логика **Inertia** (`Inertia_Follow`, опциональный пайплайн после ядра). Обратная совместимость ограничивается лишь распознаванием старой вставки `Inertia_Follow` в иерархии для поиска Offset.

Идеи ниже — для возможных будущих версий; точки расширения нужно будет заново спроектировать (отдельный модуль или хук после ядра в `tag_embedded`).

---

## Lookahead

- **Идея:** камера слегка опережает траекторию или смотрит вперёд по velocity.
- **Реализация (черновик):** буфер позиций за N кадров, смещение Look_Target или offset.

---

## Spring camera

- Реализовано в CamRig 1.6 как Follow Spring: Amount / Response / Damping, аналитический solver 120 Hz и воспроизводимый cache.
- Вне версии остаются rotational inertia, раздельные оси, пресеты и lookahead.

---

## Cinematic (позже)

- Shot system, composition tools, auto framing.

---

## Procedural FX (позже)

- Camera drift — базовая версия добавлена в 1.4.0 (`Drift Pos`, `Drift Rot`, `Drift Frequency` в группе Shake).
- Дальше: расширенный shake, лёгкое «дыхание» камеры.

---

## Production (позже)

- Camera states, shot blending, target groups.
