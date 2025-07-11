# NormaGPT - Агент для работы с нормативной базой строительных документов

🏗️ **Агентная система с YAML-структурированными промптами для точной работы с российскими строительными нормами**

## ✨ Особенности

- **YAML-промпты**: Структурированные, читаемые инструкции для LLM вместо сложных строковых промптов
- **Агентная архитектура**: Планировщик → Исполнитель → Судья → Финализатор
- **Визуальный поиск**: Поиск по изображениям страниц нормативных документов
- **Принцип нулевого знания**: Система доверяет только данным из нормативной базы
- **Контроль качества**: Встроенная система принятия решений и обработки ошибок

## 📋 Требования

- Python 3.8+
- OpenAI API ключ
- PyYAML
- PocketFlow framework

## 🚀 Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/normagpt.git
cd normagpt
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте API ключ OpenAI:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

4. **Создайте файл `.env` с настройками:**
   ```env
   # Vespa настройки
   VESPA_LOCAL_URL=http://localhost
   VESPA_LOCAL_PORT=8080
   
   # OpenRouter настройки
   OPENAI_KEY=your-openrouter-api-key
   OPENAI_URL=https://openrouter.ai/api/v1
   ```

## 💻 Использование

### Базовый запуск

```bash
python main.py
```

Система запросит ваш вопрос по строительным нормам. Примеры вопросов:
- "Какая минимальная толщина защитного слоя бетона для плиты перекрытия?"
- "Какие требования к арматуре класса A500?"
- "Как рассчитать несущую способность железобетонной балки?"

### Тестирование YAML-промптов

```bash
python utils/prompts.py
```

### Компоненты системы

#### 1. **Планировщик** (`PlannerNode`)
- Анализирует запрос пользователя
- Создает структурированный план поиска
- Использует YAML-промпт с принципами нулевого знания

#### 2. **Исполнитель** (`ExecutorNode`)
- Выполняет шаги плана
- Осуществляет визуальный поиск документов
- Анализирует найденные изображения

#### 3. **Судья** (`JudgeNode`)
- Оценивает качество результатов
- Принимает решения о продолжении/перепланировании
- Контролирует релевантность источников

#### 4. **Финализатор** (`FinalizerNode`)
- Создает итоговый ответ
- Форматирует результат в структуре Markdown
- Добавляет рекомендации и уточнения

## 🏗️ Архитектура

```mermaid
flowchart TD
    start[Начало] --> planner[Planер: YAML-промпт планирования]
    planner --> executor[Исполнитель: Поиск + анализ]
    executor --> judge[Судья: Контроль качества]
    
    judge -->|CONTINUE| executor
    judge -->|REPLAN| planner
    judge -->|FINALIZE| finalizer[Финализатор: Итоговый ответ]
    judge -->|HUMAN_REVIEW| human[Требуется человек]
    
    finalizer --> end[Завершение]
    human --> end
```

## 📁 Структура проекта

```
normagpt/
├── main.py                 # Точка входа
├── flow.py                 # Определение агентного графа
├── nodes.py                # Узлы агентной системы
├── docs/
│   ├── design.md          # Дизайн-документ системы
│   └── improvements.md    # Архитектурные улучшения
├── prompts/               # Промпты в отдельных файлах
│   ├── planner.txt        # Улучшенный промпт планировщика
│   ├── analyzer.txt       # Улучшенный промпт анализатора
│   ├── judge.txt          # Улучшенный промпт судьи
│   └── finalizer.txt      # Промпт финализатора
├── utils/
│   ├── call_llm.py        # Обертка для LLM
│   ├── schemas.py         # Pydantic схемы для валидации
│   ├── prompt_loader.py   # Загрузчик промптов из файлов
│   ├── calculate.py       # Инструмент математических расчетов
│   ├── search_documents.py # Поиск в нормативной базе
│   └── parse_yaml.py      # Парсинг YAML с Pydantic валидацией
└── requirements.txt
```

## 🎯 Улучшенные промпты

Система использует улучшенные промпты, вынесенные в отдельные файлы для лучшей поддерживаемости:

### Ключевые улучшения:
- **Планировщик**: Явное описание инструмента `calculate` с примерами
- **Анализатор**: Обязательное поле `structured_output` для машиночитаемых данных  
- **Судья**: Новая стратегия `FORM_CALCULATION_STEP` для решения зацикливания
- **Pydantic валидация**: Строгая типизация всех выходных данных
principles:
  - name: "Принцип нулевого знания"
    description: "Не используй предварительные знания"
  - name: "Принцип семантической точности"  
    description: "Максимально точные ключевые слова"
output_format:
  type: "JSON"
  strictness: "Строго JSON без комментариев"
```

## 🔧 Преимущества YAML-промптов

1. **Читаемость**: Легко понять структуру и логику
2. **Модульность**: Каждый промпт можно редактировать независимо
3. **Контроль**: Точное управление поведением агента
4. **Отладка**: Простое тестирование отдельных компонентов
5. **Масштабируемость**: Легко добавлять новые принципы и правила

## 📖 Документация

- [Дизайн системы](docs/design.md) - Подробное описание архитектуры
- [PocketFlow документация](https://the-pocket.github.io/PocketFlow/) - Фреймворк для агентных систем

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT License

## 🙏 Благодарности

- [PocketFlow](https://github.com/the-pocket/PocketFlow) - Минималистичный фреймворк для LLM-агентов
- [OpenAI](https://openai.com) - GPT модели для обработки языка
- Российские строительные нормы и стандарты

---

💡 **Примечание**: Эта система использует YAML-промпты для обеспечения более структурированного и предсказуемого контроля над агентом по сравнению с традиционными строковыми промптами.
