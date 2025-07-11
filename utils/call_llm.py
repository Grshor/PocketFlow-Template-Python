from openai import OpenAI
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv не обязателен, можно использовать обычные env переменные

# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt, system_prompt=None, task_type="default", vision_content=None):    
    """
    Вызывает LLM через OpenAI-совместимый API (включая OpenRouter).
    
    Args:
        prompt (str): Пользовательский промпт
        system_prompt (str, optional): Системный промпт
        task_type (str): Тип задачи - "analyzer" или "default"
        vision_content (list, optional): Список изображений в Vision API формате
    
    Returns:
        str: Ответ от LLM
    """
    # Получаем настройки из .env файла
    api_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY", "sk-or-v1-fake-key-for-testing")
    base_url = os.environ.get("OPENAI_URL", "https://openrouter.ai/api/v1")  # Для OpenRouter или других провайдеров
    
    # Выбираем модель в зависимости от типа задачи
    if task_type == "analyzer":
        model = "qwen/qwen2.5-vl-32b-instruct:free"
    else:
        model = "deepseek/deepseek-r1-0528:free"
    
    # Создаем клиента с поддержкой кастомного URL
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # Формируем сообщения
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Формируем пользовательское сообщение
    user_message = {"role": "user", "content": []}
    
    # Добавляем текст
    if prompt:
        user_message["content"].append({
            "type": "text",
            "text": prompt
        })
    
    # Добавляем изображения если есть
    if vision_content:
        user_message["content"].extend(vision_content)
    
    # Если нет изображений, используем простой формат
    if not vision_content:
        user_message = {"role": "user", "content": prompt}
    
    messages.append(user_message)
    
    # Логируем запрос
    print(f"⏳ Отправляем запрос к модели {model}...")
    start_time = datetime.now()
    
    try:
        # Вызываем LLM с настройками генерации
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0
        )
    except Exception as e:
        print(f"❌ Ошибка вызова LLM: {e}")
        return ""
    
    end_time = datetime.now()
    response_time = (end_time - start_time).total_seconds()
    
    # Безопасно извлекаем ответ
    response_text = ""
    try:
        if getattr(r, "choices", None):
            first_choice = r.choices[0]
            if first_choice and getattr(first_choice, "message", None):
                response_text = first_choice.message.content or ""
    except Exception as e:
        print(f"⚠️ Не удалось извлечь контент из ответа модели: {e}")
        response_text = ""
    
    # Логируем результат
    print(f"✅ Получен ответ за {response_time:.2f} сек (модель: {model})")
    
    # Безопасно извлекаем информацию о токенах
    try:
        if hasattr(r, 'usage') and r.usage:
            total_tokens = getattr(r.usage, 'total_tokens', 'неизвестно')
            print(f"📊 Токены: {total_tokens}")
        else:
            print("📊 Токены: неизвестно")
    except Exception as e:
        print(f"📊 Токены: неизвестно (ошибка: {e})")
    
    if response_text:
        print(f"📝 Длина ответа: {len(response_text)} символов, {len(response_text.split())} слов")
    else:
        print("⚠️ Пустой ответ от модели")
    
    # Короткий ответ предупреждение
    if response_text and len(response_text.split()) < 5:
        print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Получен очень короткий ответ от модели {model}")
        print(f"   Ответ: '{response_text}'")
    
    return response_text
    
if __name__ == "__main__":
    # Тест с обычной задачей
    prompt = "What is the meaning of life?"
    print("Default model:", call_llm(prompt))
    
    # Тест с задачей анализа
    analyzer_prompt = "Analyze this image content"
    print("Analyzer model:", call_llm(analyzer_prompt, task_type="analyzer"))
