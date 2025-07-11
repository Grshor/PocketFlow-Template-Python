# Design Doc: NormaGPT - Агент для работы с нормативной базой строительных документов

> Please DON'T remove notes for AI

## Requirements

Система должна отвечать на вопросы пользователей о строительных нормах (ГОСТ, СП, СНиП) путем:
- Анализа запроса и планирования поиска с использованием YAML-структурированных промптов
- Поиска релевантных документов по ключевым словам (визуальный поиск)
- Извлечения информации из найденных документов
- Контроля качества и принятия решений о продолжении
- Формирования итогового ответа с источниками

**Пользовательская история**: Инженер спрашивает "Какая минимальная толщина защитного слоя бетона для плиты перекрытия?" и получает точный ответ со ссылками на конкретные пункты СП с возможностью уточнения условий эксплуатации.

## Flow Design

### Applicable Design Pattern:

**Agent Pattern** - система принимает решения на каждом шаге:
- *Context*: Запрос пользователя, текущий план, результаты поиска, история выполнения
- *Actions*: планировать → искать → анализировать → судить → финализировать

### Flow high-level Design:

1. **Planner Node**: Анализирует запрос пользователя и создает план поиска с использованием YAML-промпта
2. **Executor Node**: Выполняет шаги плана (поиск + анализ документов) с YAML-контролируемой логикой
3. **Judge Node**: Оценивает результат и принимает решение о продолжении согласно YAML-правилам
4. **Finalizer Node**: Создает итоговый ответ для пользователя с YAML-структурированным форматом

```mermaid
flowchart TD
    start[Начало] --> planner[Planner: Создание плана]
    planner --> executor[Executor: Выполнение шага]
    executor --> judge[Judge: Оценка результата]
    
    judge -->|CONTINUE| executor
    judge -->|REPLAN| planner  
    judge -->|FINALIZE| finalizer[Finalizer: Итоговый ответ]
    judge -->|HUMAN_REVIEW| human[Требуется человек]
    
    finalizer --> end[Конец]
    human --> end
```

## Utility Functions

1. **Call LLM** (`utils/call_llm.py`)
   - *Input*: prompt (str), system_prompt (str)
   - *Output*: response (str)
   - Используется всеми узлами для вызова LLM с YAML-промптами

2. **Search Documents** (`utils/search_documents.py`)
   - *Input*: semantic_keywords (list), expected_documents (list)
   - *Output*: list of document images or None
   - Выполняет визуальный поиск по базе нормативов и возвращает изображения страниц

3. **Parse JSON Response** (`utils/parse_json.py`)
   - *Input*: llm_response (str)
   - *Output*: parsed_dict or error
   - Парсит JSON-ответы от LLM с обработкой ошибок

4. **Load YAML Prompts** (`utils/prompts.py`)
   - *Input*: prompt_name (str)
   - *Output*: formatted_prompt (str)
   - Загружает и форматирует YAML-промпты в текстовые инструкции

## Node Design

### Shared Store

```python
shared = {
    "user_query": "Исходный запрос пользователя",
    "plan": {
        "goal": "Цель плана",
        "steps": [{"step_number": 1, "action": "...", "tool": "...", ...}],
        "current_step_index": 0
    },
    "scratchpad": {
        "priority_documents": ["СП 63.13330.2018"],
        "query_domain": "concrete_structure_design",
        "rejected_sources": {},
        "search_hypotheses": []
    },
    "execution_history": [],
    "step_results": {},
    "final_answer": None,
    "status": "planning|executing|judging|finalizing|completed|error"
}
```

### Node Steps

1. **Planner Node**
  - *Purpose*: Создает план поиска на основе запроса пользователя с использованием YAML-промпта
  - *Type*: Regular
  - *Steps*:
    - *prep*: Читает "user_query" из shared store
    - *exec*: Вызывает LLM с YAML-промптом планировщика для создания плана
    - *post*: Сохраняет план в shared["plan"], устанавливает status="executing"

2. **Executor Node**
  - *Purpose*: Выполняет текущий шаг плана (поиск + анализ) согласно YAML-инструкциям
  - *Type*: Regular
  - *Steps*:
    - *prep*: Читает текущий шаг из shared["plan"]["steps"]
    - *exec*: Выполняет поиск документов + анализ через LLM с YAML-промптом исполнителя
    - *post*: Сохраняет результат в shared["step_results"], обновляет current_step_index

3. **Judge Node**
  - *Purpose*: Оценивает результат и принимает решение о следующем действии согласно YAML-правилам
  - *Type*: Regular  
  - *Steps*:
    - *prep*: Читает все данные (план, результаты, историю)
    - *exec*: Вызывает LLM с YAML-промптом судьи для принятия решения
    - *post*: Обновляет status и возвращает решение как action ("CONTINUE", "REPLAN", "FINALIZE", "HUMAN_REVIEW")

4. **Finalizer Node**
  - *Purpose*: Создает итоговый ответ пользователю с использованием YAML-структуры
  - *Type*: Regular
  - *Steps*:
    - *prep*: Читает все накопленные результаты и пользовательский запрос
    - *exec*: Вызывает LLM с YAML-промптом финализатора для создания финального ответа
    - *post*: Сохраняет ответ в shared["final_answer"], status="completed"

