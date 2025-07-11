import yaml
import re

def parse_yaml_response(llm_response):
    """
    Парсит YAML-ответ от LLM с обработкой ошибок
    
    Args:
        llm_response (str): Ответ от LLM, который должен содержать YAML
    
    Returns:
        dict: Распарсенный YAML или словарь с ошибкой (никогда не возвращает None)
    """
    # Проверяем что llm_response не None и не пустой
    if not llm_response or not llm_response.strip():
        return {
            "error": "Пустой ответ от LLM",
            "raw_response": str(llm_response)
        }
    
    def preprocess_yaml_content(content):
        """Предобработка YAML контента для корректного парсинга LaTeX формул"""
        # Простое экранирование проблемных символов в YAML
        # Экранируем обратные слеши в LaTeX формулах
        content = content.replace('\\(', '\\\\(')
        content = content.replace('\\)', '\\\\)')
        content = content.replace('\\{', '\\\\{')
        content = content.replace('\\}', '\\\\}')
        content = content.replace('\\_', '\\\\_')
        content = content.replace('\\^', '\\\\^')
        
        return content
    
    try:
        # Пытаемся найти YAML в ответе
        # Сначала пробуем парсить весь ответ как YAML
        try:
            preprocessed_response = preprocess_yaml_content(llm_response.strip())
            result = yaml.safe_load(preprocessed_response)
            # Проверяем что результат не None (может быть если YAML содержит только null)
            if result is None:
                return {
                    "error": "YAML парсер вернул None",
                    "raw_response": llm_response
                }
            # Проверяем что результат это словарь (структурированные данные)
            if not isinstance(result, dict):
                return {
                    "error": f"YAML не содержит структурированных данных (словарь), получен {type(result).__name__}",
                    "raw_response": llm_response
                }
            return result
        except yaml.YAMLError:
            pass
        
        # Ищем YAML блок в тексте
        yaml_match = re.search(r'```yaml\s*(.*?)\s*```', llm_response, re.DOTALL)
        if yaml_match:
            preprocessed_yaml = preprocess_yaml_content(yaml_match.group(1))
            try:
                result = yaml.safe_load(preprocessed_yaml)
                if isinstance(result, dict):
                    return result
            except yaml.YAMLError:
                pass
        
        # Ищем просто блок кода
        yaml_match = re.search(r'```\s*(.*?)\s*```', llm_response, re.DOTALL)
        if yaml_match:
            preprocessed_yaml = preprocess_yaml_content(yaml_match.group(1))
            try:
                result = yaml.safe_load(preprocessed_yaml)
                if isinstance(result, dict):
                    return result
            except yaml.YAMLError:
                pass
        
        return {
            "error": "YAML не найден в ответе",
            "raw_response": llm_response
        }
        
    except yaml.YAMLError as e:
        return {
            "error": f"Ошибка парсинга YAML: {str(e)}",
            "raw_response": llm_response
        }
    except Exception as e:
        return {
            "error": f"Неожиданная ошибка: {str(e)}",
            "raw_response": llm_response
        }

# Оставляем старое имя для совместимости
parse_json_response = parse_yaml_response

if __name__ == "__main__":
    # Тесты
    test_responses = [
        'status: success\ndata: test',
        '```yaml\nstatus: success\ndata: test\n```',
        'Вот результат:\n```yaml\nstatus: success\ndata: test\n```\nи комментарий',
        'Неправильный формат',
        # Тест с LaTeX формулами
        '''```yaml
status: success
output:
  data: |
    Для расчёта используйте формулу: \\( n_{\\text{max}} = \\left\\lfloor \\frac{d}{c} \\right\\rfloor \\)
```'''
    ]
    
    for response in test_responses:
        result = parse_yaml_response(response)
        print(f"Ответ: {response[:50]}...")
        print(f"Результат: {result}")
        print("---") 