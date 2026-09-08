# CamRig 1.6.0 — development

Орбитальный камерный риг для Cinema 4D 2026.2. Концепция сохранена: круг → Follow → Offset → Spring Offset → камера → FX (Rotation, Shake, Drift).

Управление находится в User Data корня Cam_Rig. В 1.5 добавлены свободные обороты Orbit, высота/центр/HPB круга, независимый Orbit Center, Aim Offset и независимый автофокус. В 1.6 добавлен Follow Spring: позиционная инерция и затухающие колебания с воспроизводимым расчётом. Сцена хранит полный runtime в трёх Python Tags.

- [Установка](INSTALL.md)
- [Таблица всех 37 параметров](docs/UDref.md)
- [Архитектура и поведение](docs/SUMMARY.md)
- [Upgrade старых ригов](docs/UPGRADE_1_5.md)
- [Follow Spring 1.6](docs/SPRING_1_6.md)
- [Проверки и оставшиеся ограничения](docs/ACCEPTANCE_1_6.md)
- [MCP runbook](docs/MCP_SETUP.md)
- [Изменения](CHANGELOG.md)

Версия development, не публичный релиз. Автоматические Show/Hide HUD не реализованы: Python API C4D не предоставляет создание нативных HUD-элементов. Ручной Add to HUD возможен; альтернативный интерфейс требует выбора владельца.

Redshift необязателен: предусмотрена стандартная камера. Условия лицензирования не менялись; существующий MIT LICENSE конфликтует с коммерческим текстом production-сборщика. До решения владельца сборку не распространять.
