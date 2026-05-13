---

# 14. User Data Reference

Этот раздел описывает все параметры **User Data**, расположенные на объекте **Main_Camera**.

User Data формируют основной интерфейс рига и используются Python Tag для управления системой.

---

# Motion

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Orbit | Float / Slider | -360 → 360 | вращение камеры вокруг центра |
| Radius | Float / Slider | 0 → ∞ | расстояние камеры от центра |
| Height | Float | -∞ → ∞ | вертикальное смещение камеры |
| Spline Position | Float | 0 → 100 | положение камеры вдоль сплайна |
| Speed Offset | Float | -∞ → ∞ | дополнительное смещение движения |

---

# Offset

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Offset X | Float | -∞ → ∞ | локальное смещение камеры по X |
| Offset Y | Float | -∞ → ∞ | локальное смещение камеры по Y |
| Offset Z | Float | -∞ → ∞ | локальное смещение камеры по Z |

---

# Rotation

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Heading | Float | -180 → 180 | поворот камеры по горизонтали |
| Pitch | Float | -180 → 180 | наклон камеры |
| Bank | Float | -180 → 180 | крен камеры |

---

# Lens

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Focal Length | Float | 10 → 300 | фокусное расстояние камеры |
| Focus Distance | Float | 0 → ∞ | дистанция фокусировки |
| Depth of Field | Bool | on/off | включает DOF |

---

# Targeting

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Target A | Link | object | первая цель |
| Target B | Link | object | вторая цель |
| Use Target B | Bool | on/off | включает вторую цель |
| Target Blend | Float / Slider | 0 → 100 | смешивание между целями |

---

# Camera FX

| Parameter | Type | Range | Description |
|----------|------|------|-------------|
| Shake Enable | Bool | on/off | включает эффект тряски |
| Shake Amplitude | Float | 0 → ∞ | амплитуда тряски |
| Shake Frequency | Float | 0 → ∞ | частота шума |
| Noise Seed | Integer | 0 → ∞ | seed генератора шума |

---

# Utilities

| Parameter | Type | Description |
|----------|------|-------------|
| Snap to Target A | Button | мгновенно переводит взгляд на Target A |
| Snap to Target B | Button | мгновенно переводит взгляд на Target B |
| Reset Offsets | Button | сбрасывает Offset параметры |
| Create Targets | Button | создаёт Target_A, Target_B, Look_Target |
| Frame Selected | Button | устанавливает камеру относительно выбранного объекта |

---

# Internal Parameters

Эти параметры используются системой и могут быть скрыты от пользователя.

| Parameter | Type | Description |
|----------|------|-------------|
| Internal Look Target | Link | ссылка на объект Look_Target |
| Internal Follow Node | Link | ссылка на объект Follow |
| Internal Offset Node | Link | ссылка на объект Offset |
| Internal Camera | Link | ссылка на RS_CAM |

---

# JSON-шаблон (ud_template.json)

Параметры типа **real** (Float) поддерживают поле `"interface"` — как отображать значение в C4D. Допустимые значения (соответствуют выпадающему списку Interface в свойствах User Data):

| Значение в JSON | Интерфейс в C4D |
|-----------------|------------------|
| `float` | Float |
| `slider`, `float_slider` | Float Slider |
| `float_slider_no_editfield` | Float Slider (No Editfield) |
| `latitude_longitude`, `latlong` | Latitude/Longitude |
| `rsslider` | RSSlider |