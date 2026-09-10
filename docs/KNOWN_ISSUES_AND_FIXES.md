# CamRig — Известные проблемы и решения

Документ фиксирует ошибки, возникавшие при разработке плагина, и способы их устранения.  
Не мержить ветки без проверки — некоторые фиксы зависят от ветки.

---

## 1. BaseContainer не имеет метода `.get()`

**Ошибка:**
```text
'c4d.BaseContainer' object has no attribute 'Get'
'c4d.BaseContainer' object has no attribute 'get'
```

**Причина:** `c4d.BaseContainer` — контейнер C4D, доступ к полям через `bc[id]`, а не через `.get()` как у словаря.

**Решение:**
- Не вызывать `bc.get(key)` — использовать `bc[c4d.DESC_NAME]` и т.п.
- Для проверки наличия полей — `try/except` или проверка типа:
  ```python
  # Неверно:
  value = bc.get(c4d.DESC_NAME)
  # Верно:
  try:
      value = bc[c4d.DESC_NAME] or ""
  except Exception:
      value = ""
  ```
- Читать UD в **словарь** через `_read_rig_ud(rig)` — словарь уже поддерживает `.get()`.
- В `_set_rig_ud_by_name` искать UD по имени итерируясь по `rig.GetUserDataContainer()`, не используя `.get()` у `BaseContainer`.

---

## 2. AddCheckbox — `initw` обязателен

**Ошибка:**
```text
TypeError: Required argument 'initw' (pos 3) not found
self.AddCheckbox(id=ID_RESET_ORBIT, flags=c4d.BFH_LEFT, name="Orbit", initval=False)
```

**Причина:** Сигнатура `AddCheckbox` в C4D Python: `(id, flags, initw, inith, name, initval=...)`.  
Позиционный аргумент `initw` должен быть указан.

**Решение:**
```python
self.AddCheckbox(ID_RESET_ORBIT, c4d.BFH_LEFT, 0, 0, "Orbit", initval=False)
```

---

## 3. c4d.gui.MessageDialog — неверный вызов

**Ошибка:**
```text
TypeError: message() missing 1 required positional argument: 'data'
```

**Причина:** `c4d.gui.MessageDialog()` ожидает один аргумент — строку сообщения.

**Решение:**
```python
c4d.gui.MessageDialog("Текст сообщения")
```

---

## 4. AddComboBox — неверные аргументы

**Ошибка:**
```text
TypeError: 'customlayout' is an invalid keyword argument for this function
```

**Причина:** В C4D Python `AddComboBox` не поддерживает `customlayout`.

**Решение:**
```python
self.AddComboBox(ID_COMBO_RIGS, c4d.BFH_SCALEFIT, 200, 0)
```

---

## 5. ScrollGroupEnd vs GroupEnd

**Ошибка:**
```text
AttributeError: 'CamRigDialog' object has no attribute 'ScrollGroupEnd'
```

**Причина:** Метода `ScrollGroupEnd` нет, для закрытия ScrollGroup используется `GroupEnd()`.

**Решение:** После `ScrollGroupBegin` вызывать `GroupEnd()` дважды (внутренняя группа и ScrollGroup).

---

## 6. SetTimer — неверная сигнатура

**Ошибка:**
```text
TypeError: function takes at most 1 argument (2 given)
self.SetTimer(ID_TIMER_SYNC, 100)
```

**Причина:** Сигнатура `SetTimer` отличается в разных версиях C4D.

**Решение:** Проверить документацию: `self.SetTimer(100)` или `self.SetTimer(ID)`.

---

## 7. Reset selected — `__setitem__` с float

**Ошибка:**
```text
[CamRig] ERROR: Reset selected failed: __setitem__ got unexpected type 'float'.
```

**Причина:** Для bool-параметров UD нужно передавать `int`, не `float`.

**Решение:** В `_set_ud_value_safe` приводить bool к int.

---

## 8. PLUGIN_ID_RIG_TAG отсутствует

**Ошибка:**
```text
AttributeError: module 'camrig.config' has no attribute 'PLUGIN_ID_RIG_TAG'
```

**Решение:** Добавить `PLUGIN_ID_RIG_TAG = 1244570` в `config.py` или использовать альтернативу (имя тега).

---

## 9. RegisterTagPlugin — аргументы

**Ошибка:**
```text
TypeError: Required argument 'g' (pos 4) not found
'dat' is an invalid keyword argument
```

**Причина:** Сигнатура `RegisterTagPlugin` менялась между версиями C4D.

**Решение:** Сверяться с SDK для своей версии. Параметр `dat` устарел, использовать `g` для класса.

---

## 10. Global resource

**Ошибка:**
```text
Could not initialize global resource for the plugin
```

**Решение:** Для иконки передавать `None` или убрать параметр, если ресурс не загружен.

---

## 11. Orbit — радианы vs градусы

**Проблема:** Orbit не управляется из UI, двойное преобразование.

**Причина:** `DESC_UNIT_DEGREE` + `orbit/360` + `DegToRad()`.

**Решение:** Хранить в градусах, убрать `unit=_UNIT_DEGREE` у orbit/rotation в rig_builder.

---

## 12. Дублирование имён UD (Orbit group и Orbit float)

**Решение:** Пропускать группы при поиске по имени: проверять `bc[c4d.DESC_DATATYPE] != c4d.DTYPE_GROUP`.

---

## 13. Кнопки Reset All / Reset Selected не видны в Attribute Manager

**Проблема:** В Manage User Data кнопки есть, но в панели атрибутов (Attribute Manager) при выборе рига их не видно.

**Решение:**
- В коде для кнопок UD выставляется `bc[c4d.DESC_HIDE] = False` при создании.
- После создания рига плагин автоматически выбирает созданный rig — в AM должны отображаться User Data.
- В Attribute Manager нужно раскрыть секцию **User Data**, затем группу **Reset** — внизу списка будут кнопки «Reset All» и «Reset Selected».

---

## 14. Кнопки Reset All / Reset Selected видны, но ничего не делают при нажатии

**Симптом:** Кнопки появились в User Data рига (AM), нажатие не вызывает никакого эффекта.

**Подтверждённая корневая причина (runtime-логами):**  
`c4d.MSG_DESCRIPTION_COMMAND = 18` в C4D 2026. Python Tag на объекте типа `Onull` получает `MSG_DESCRIPTION_INITUNDO = 19` (которое содержит `data["descid"]`) — но **никогда не получает msg 18 (кнопочное событие)**. Это архитектурное ограничение C4D: сообщение `MSG_DESCRIPTION_COMMAND` от UD-кнопок на Null-объекте не проксируется к Python Tag'ам, прикреплённым к этому объекту.

**Дополнительная деталь:** В C4D 2026 (Python 3.11) `data` для description-сообщений — это Python dict с ключом `"descid"` (не `"id"` и не BaseContainer). Так что `data.get("id")` вернул бы `None` даже если бы сообщение дошло.

**Решение:**  
Перенести Reset-кнопки из User Data рига (AM) в **GeDialog плагина**. `GeDialog.Command()` работает гарантированно. Кнопки "Reset All" и "Reset Selected" добавлены в диалог вместе с чекбоксами выбора групп. Диалог сам находит активный риг через `_find_rig(doc)`.

| Где | Что |
|---|---|
| AM (User Data рига) | Чекбоксы Reset Orbit/Offset/Rotation/Focal/Target/Shake — отмечаешь что сбросить |
| Диалог плагина | Кнопки **Reset All** и **Reset Selected** — реально выполняют сброс |

---

## Сводная таблица

| № | Проблема | Решение |
|---|----------|---------|
| 1 | BaseContainer.get | Использовать dict / bc[id] |
| 2 | AddCheckbox initw | Указать initw, inith |
| 3 | MessageDialog | Один аргумент — строка |
| 4 | AddComboBox | Убрать customlayout |
| 5 | ScrollGroupEnd | GroupEnd() |
| 6 | SetTimer | Проверить сигнатуру |
| 7 | __setitem__ float | bool → int |
| 8 | PLUGIN_ID_RIG_TAG | Добавить в config |
| 9 | RegisterTagPlugin | Проверить параметры |
|10 | Global resource | icon=None |
|11 | Orbit radians | Убрать unit degree |
|12 | UD Orbit group | Пропускать DTYPE_GROUP |
|13 | Кнопки не в AM | DESC_HIDE = False; раскрыть User Data → Reset |
|14 | Кнопки не работают | data.get() на BaseContainer → _extract_desc_id_from_msg() |

## 15. QA lifecycle записывал marker в пользовательский документ

**Проблема:** ранний контрактный harness добавлял служебный marker в
`BaseDocument`. При исчезновении пустого документа Cinema 4D marker терялся,
а восстановление по имени мог выбрать другой документ.

**Решение:** marker удалён. Harness хранит точную ссылку на исходный документ
в краткоживущем реестре Python-интерпретатора C4D и заранее создаёт проверенный
`.c4d` snapshot. Snapshot используется только если исходный объект больше не
зарегистрирован. Такой результат имеет статус `RECOVERED`, а не обычный `PASS`.

## 16. Ссылка на уничтоженный BaseDocument вызывала ReferenceError

**Проблема:** после удаления исходного документа сравнение dead Python wrapper с
элементами списка документов приводило к `ReferenceError` и скрывало настоящий
сценарий аварийного восстановления.

**Решение:** проверка регистрации документа теперь безопасно обрабатывает
`None` и уничтоженные C4D wrappers. Принудительное удаление источника покрыто
отдельным live regression-тестом и проверяет fingerprint восстановленного
snapshot.

## 17. Windows npx child оставался после завершения stdio-теста

**Проблема:** закрытие MCP `StdioClientTransport` завершало `npx.cmd`, но в
некоторых запусках оставляло дочерний Node-процесс Cinema 4D MCP.

**Решение:** proxy и acceptance runner сохраняют PID собственного child tree и
при завершении закрывают только этот процессный tree через `taskkill /T /F`.
Дополнительные listening-порты не создаются; bridge Cinema 4D не затрагивается.

---

## Ветки (без мержа)

- `master` — основная
- `feature/rig-control-dialog`
- `feature/ud-descid`
- `patch/ud-lookup-fix`
