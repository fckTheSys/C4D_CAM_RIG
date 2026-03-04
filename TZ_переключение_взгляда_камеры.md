# Техническое задание: система плавного переключения взгляда камеры

## 1. Цель

Реализовать систему управления камерой, позволяющую плавно переключать направление взгляда камеры между несколькими таргетами с возможностью анимации веса влияния каждого таргета.

Система должна быть удобной для аниматоров и позволять контролировать направление взгляда через один параметр Blend или веса таргетов.

---

## 2. Основная логика

- Камера всегда смотрит на **виртуальный таргет (LookTarget)**.
- Этот таргет вычисляется как смешивание позиций нескольких целей.

**Формула (два таргета):**

```
LookTargetPosition = (1 - Blend) * PositionA + Blend * PositionB
```

где Blend задаётся в диапазоне 0–100 (в интерфейсе), внутри расчёта используется нормализованное значение t = Blend/100.

**Общая формула для N таргетов (расширение на будущее):**

```
LookTargetPosition = Σ(TargetPosition_i * Weight_i)
```

где Σ Weight_i = 1.

---

## 3. Термины и соответствие объектам в плагине

| Термин в ТЗ      | Объект в сцене (плагин Cam Rig Builder) |
|------------------|----------------------------------------|
| **LookTarget**   | Null **Look_Target** (виртуальная цель камеры) |
| **Controller**   | Объект **Main_Camera** (spline circle) — на нём все параметры и Python Tag |
| **Target A**     | Null **Target_A** (или объект, назначенный в User Data «Target A») |
| **Target B**     | Null **Target_B** (или объект, назначенный в User Data «Target B») |

- **Target Tag** — стандартный тег Cinema 4D «Target Expression» на камере RS_CAM; ссылается на Look_Target.
- **Target_A / Target_B** — объекты, на которые может смотреть камера (персонажи, предметы, точки в пространстве). В риге по умолчанию это null'ы Target_A и Target_B; через User Data их можно заменить на любые объекты сцены.

---

## 4. Иерархия объектов (как создаёт плагин)

```
Cam_Rig (null)
├── Target_A (null)
├── Target_B (null)
├── Look_Target (null)   ← виртуальный таргет; позиция вычисляется по Blend
└── Main_Camera (spline circle)   ← Controller: User Data + Python Tag
    └── Follow (null) + Align to Spline
        └── Offset (null)
            └── RS_CAM (camera) + Target Expression → Look_Target
                └── FX_CAM (camera) + Vibrate
```

Камера автоматически поворачивается на Look_Target через Target Tag.

---

## 5. Параметры управления

Контроллер (**Main_Camera**) имеет следующие параметры (User Data):

| Параметр      | Тип    | Диапазон | Описание |
|---------------|--------|----------|----------|
| **Target Blend** | Float  | 0–100    | 0 → камера смотрит на Target A; 100 → на Target B. Плавное смешивание между A и B. |
| **Use Target B** | Bool   | —        | Если выключен — камера смотрит только на Target A. Если включен — смешивание по Blend между Target A и Target B. |
| **Target A**  | Link   | —        | Объект первой цели (по умолчанию null Target_A). |
| **Target B**  | Link   | —        | Объект второй цели (по умолчанию null Target_B). |

Остальные параметры рига (Orbit, Radius, Offset, Rotation, Focal Length, Shake и т.д.) описаны в общей документации плагина.

---

## 6. Алгоритм (псевдокод)

```
posA = TargetA.position
posB = TargetB.position

// Вычислить позицию LookTarget
t = Blend / 100   // нормализация 0–100 → 0–1
lookPos = (1 - t) * posA + t * posB

// Установить позицию LookTarget
LookTarget.position = lookPos

// Камера автоматически поворачивается на LookTarget через Target Tag.
```

Если **Use Target B** выключен, используется только posA (LookTarget.position = posA).

---

## 7. Требования к анимации

Система поддерживает:

- ключевую анимацию параметра **Target Blend**;
- плавные переходы через F-Curve;
- управление в Timeline.

Параметр Blend анимируется через User Data на объекте Main_Camera (ключи и F-Curves в Timeline Cinema 4D).

**Пример:**

- Frame 0: Blend = 0 (взгляд на Target A)
- Frame 60: Blend = 100 (взгляд на Target B)

---

## 8. Расширение системы (на будущее)

Система должна позволять масштабирование до **N таргетов**.

**Формула:**

```
LookTarget = Σ(Target_i * Weight_i)
```

**Ограничения:** Σ Weight_i = 1.

**Текущая реализация:** в плагине Cam Rig Builder реализованы только два таргета (Target A, Target B) и один параметр Blend. Это эквивалентно весам: Weight_A = 1 − t, Weight_B = t, где t = Blend/100. Расширение до произвольного числа таргетов с отдельными весами планируется в следующих версиях.

---

## 9. Реализация

- **Плагин:** Cam Rig Builder (команда из меню Cinema 4D).
- При вызове команды создаётся риг с объектами Cam_Rig, Target_A, Target_B, Look_Target, Main_Camera и иерархией камер (RS_CAM, FX_CAM).
- Все параметры переключения взгляда (Target A, Target B, Use Target B, Target Blend) находятся на объекте **Main_Camera** в User Data.
- Логика смешивания позиций и обновления Look_Target выполняется каждый кадр через Python Tag на Main_Camera.
