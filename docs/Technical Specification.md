# Camera Rig Builder
## Technical Specification
Cinema 4D 2026

---

# 1. Overview

Camera Rig Builder — это профессиональный риг камеры для Cinema 4D, предназначенный для удобной анимации, постановки кадра и управления направлением взгляда.

Основная задача системы — предоставить аниматору **единый контроллер**, через который можно управлять:

- движением камеры
- положением камеры в пространстве
- направлением взгляда
- фокусным расстоянием
- вторичными эффектами камеры
- служебными командами

Интерфейс рига реализован через **User Data** на корне рига (**Cam_Rig**). Логика выполняется в **Python Tag** на Main_Camera; параметры читаются с родителя (rig). Основной контроллер для аниматора — объект **Main_Camera** (круг по орбите); создание рига и сброс — через диалог плагина.

- **User Data:** на Cam_Rig (главный родитель); структура задаётся JSON-шаблоном `camrig/ud_template.json`.
- **Документация по ошибкам и фиксам:** см. [KNOWN_ISSUES_AND_FIXES.md](KNOWN_ISSUES_AND_FIXES.md).

---

# 2. System Architecture

Риг создаёт следующую структуру объектов:

Cam_Rig

├── Target_A  
├── Target_B  

├── Look_Target  

└── Main_Camera  
  └── Follow  
    └── Offset  
      └── RS_CAM  
        └── FX_CAM  

---

# 3. Object Description

### Cam_Rig
Главный контейнер рига.

Содержит все элементы системы.

---

### Main_Camera
Основной контроллер рига (сплайн-круг по орбите).

Содержит:

- Python Tag (логика орбиты, offset, focal, shake, target blend)
- дочернюю цепочку Follow → Offset → RS_CAM → FX_CAM

Параметры **User Data** хранятся на **Cam_Rig** (родитель); Python Tag читает их с rig. Аниматор выделяет Main_Camera или любой объект рига для работы в Attribute Manager.

---

### Follow
Служебный объект для движения камеры.

Используется для:

- движения по сплайну
- орбитального движения
- базового позиционирования

---

### Offset
Используется для локальных смещений камеры.

Позволяет корректировать кадр без изменения основной структуры рига.

---

### RS_CAM
Основная рабочая камера.

Формирует основной кадр.

---

### FX_CAM
Дополнительная камера для эффектов.

Используется для:

- Camera Shake
- Noise
- вторичных движений

---

### Look_Target
Виртуальная точка, на которую направляется камера.

Камера не смотрит напрямую на объекты сцены.

Она всегда ориентируется на **Look_Target**.

---

### Target_A / Target_B
Цели, между которыми камера может переключать взгляд.

---

# 4. Camera Target System

На камере **RS_CAM** используется стандартный тег Cinema 4D:

Target Expression

Связь:

RS_CAM → Target Expression → Look_Target

Позиция Look_Target вычисляется системой рига.

Это позволяет управлять направлением камеры без прямого вращения.

---

# 5. User Interface (User Data)

Интерфейс рига реализован через **User Data**.

Все элементы управления находятся на объекте:

Main_Camera

Используемые типы данных:

| Type | Description |
|-----|-------------|
| Float | числовые параметры |
| Boolean | переключатели |
| Link | ссылки на объекты |
| Slider | регулировка значений |
| Cycle | выбор режима |
| Button | запуск команды |
| Group | организация интерфейса |

---

# 6. UI Structure

Интерфейс рига организован в логические группы.

---

## Motion

Управление движением камеры.

Параметры:

- Orbit
- Radius
- Height
- Spline Position
- Speed Offset

---

## Offset

Локальные смещения камеры.

Параметры:

- Offset X
- Offset Y
- Offset Z

---

## Rotation

Ручная корректировка поворота камеры.

Параметры:

- Heading
- Pitch
- Bank

---

## Lens

Оптические параметры камеры.

Параметры:

- Focal Length
- Focus Distance
- Depth of Field

---

## Targeting

Управление направлением взгляда.

Параметры:

| Parameter | Type | Description |
|----------|------|-------------|
| Target A | Link | первая цель |
| Target B | Link | вторая цель |
| Use Target B | Bool | включает вторую цель |
| Target Blend | Float | смешивание между целями |

---

## Camera FX

Вторичные эффекты камеры.

Параметры:

- Shake Enable
- Shake Amplitude
- Shake Frequency
- Noise Seed

---

## Utilities

Служебные функции рига.

Реализованы через кнопки.

---

# 7. Button Data Type

Тип данных **Button** используется для выполнения команд.

Кнопка **не хранит значение**, как обычные параметры.

Она работает как **триггер события**.

При нажатии кнопки Cinema 4D отправляет сообщение:

MSG_DESCRIPTION_COMMAND

Python Tag или плагин перехватывает это событие и выполняет действие.

Таким образом кнопка используется для:

- запуска функций
- сервисных операций
- автоматизации рига

---

# 8. Button Usage

Примеры кнопок:

---

### Snap to Target A

Переводит взгляд камеры на Target A.

Target Blend = 0

---

### Snap to Target B

Переводит взгляд камеры на Target B.

Target Blend = 100

---

### Reset Offsets

Сбрасывает локальные смещения камеры.

Offset X = 0  
Offset Y = 0  
Offset Z = 0  

---

### Create Targets

Создаёт необходимые объекты:

Target_A  
Target_B  
Look_Target  

если они отсутствуют.

---

### Frame Selected

Устанавливает target или позицию камеры относительно выбранного объекта.

---

# 9. Target Blending System

Система поддерживает плавное смешивание между двумя целями.

Параметры:

| Parameter | Type | Range |
|----------|------|------|
| Target A | Link | object |
| Target B | Link | object |
| Use Target B | Bool | on/off |
| Target Blend | Float | 0–100 |

---

## Formula

t = Blend / 100

LookTargetPosition =
(1 - t) * Position(Target A)
+
t * Position(Target B)

---

### Behaviour

| Blend | Result |
|------|-------|
| 0 | камера смотрит на Target A |
| 50 | смешанный взгляд |
| 100 | камера смотрит на Target B |

---

# 10. Animation

Основные параметры рига поддерживают анимацию.

Наиболее используемые анимируемые параметры:

- Orbit
- Radius
- Offset
- Rotation
- Focal Length
- Target Blend

Пример анимации:

Frame 0  
Blend = 0

Frame 60  
Blend = 100

Результат: камера плавно переводит взгляд между целями.

---

# 11. Python Tag Logic

Основная логика рига выполняется через:

Python Tag  
(Main_Camera)

Python Tag выполняет:

1. чтение значений User Data
2. обработку кнопок
3. вычисление позиции Look_Target
4. обновление трансформаций объектов

Алгоритм выполняется **каждый кадр**.

---

# 12. Compatibility

Риг разработан для:

Cinema 4D 2026

Используемые технологии:

- User Data
- Python Tag
- Target Expression
- Object hierarchy

Это обеспечивает стабильную работу без дополнительных зависимостей.

---

# 13. Future Extensions

Планируемые расширения системы:

- поддержка нескольких таргетов
- система весов таргетов
- расширенные операторские пресеты
- автоматическое кадрирование
- bake анимации камеры

---

# 14. Документация и код

- **[UDref.md](UDref.md)** — справочник по параметрам User Data и допустимым значениям `interface` в JSON-шаблоне.
- **[KNOWN_ISSUES_AND_FIXES.md](KNOWN_ISSUES_AND_FIXES.md)** — известные ошибки C4D API и способы их обхода (BaseContainer, AddCheckbox, SetTimer и др.).
- **camrig/ud_template.json** — шаблон групп и параметров UD; при создании рига используется при успешной загрузке, иначе — fallback в коде.