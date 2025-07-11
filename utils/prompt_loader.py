"""Утилита для загрузки промптов из отдельных файлов.

Реализует принцип разделения кода и конфигурации для лучшей поддерживаемости системы.
"""

import os
from pathlib import Path
from typing import Dict, Optional

class PromptLoader:
    """Загрузчик промптов из файловой системы"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Инициализация загрузчика промптов.
        
        Args:
            prompts_dir: Директория с файлами промптов
        """
        self.prompts_dir = Path(prompts_dir)
        self._prompt_cache: Dict[str, str] = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        Загружает промпт из файла.
        
        Args:
            prompt_name: Имя промпта (без расширения)
            
        Returns:
            Содержимое файла промпта
            
        Raises:
            FileNotFoundError: Если файл промпта не найден
        """
        # Проверяем кэш
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]
        
        # Пробуем разные расширения файлов
        extensions = ['.txt', '.md', '.prompt']
        prompt_path = None
        
        for ext in extensions:
            potential_path = self.prompts_dir / f"{prompt_name}{ext}"
            if potential_path.exists():
                prompt_path = potential_path
                break
        
        if not prompt_path:
            available_files = list(self.prompts_dir.glob("*"))
            raise FileNotFoundError(
                f"Файл промпта '{prompt_name}' не найден в {self.prompts_dir}. "
                f"Доступные файлы: {[f.name for f in available_files]}"
            )
        
        try:
            content = prompt_path.read_text(encoding="utf-8")
            # Кэшируем содержимое
            self._prompt_cache[prompt_name] = content
            return content
        except UnicodeDecodeError as e:
            raise ValueError(f"Ошибка кодировки при чтении файла {prompt_path}: {e}")
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Загружает и форматирует промпт с подстановкой переменных.
        
        Args:
            prompt_name: Имя промпта
            **kwargs: Переменные для подстановки
            
        Returns:
            Отформатированный промпт
        """
        template = self.load_prompt(prompt_name)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise ValueError(
                f"Отсутствует переменная '{missing_var}' для промпта '{prompt_name}'"
            )
    
    def clear_cache(self):
        """Очищает кэш промптов"""
        self._prompt_cache.clear()
    
    def get_available_prompts(self) -> list:
        """Возвращает список доступных промптов"""
        if not self.prompts_dir.exists():
            return []
        
        prompts = []
        for file_path in self.prompts_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.prompt']:
                prompts.append(file_path.stem)
        
        return sorted(prompts)

# Глобальный экземпляр загрузчика
_prompt_loader = PromptLoader()

# Функции для обратной совместимости
def load_prompt_from_file(prompt_name: str) -> str:
    """Загружает промпт из файла"""
    return _prompt_loader.load_prompt(prompt_name)

def get_planner_prompt() -> str:
    """Возвращает промпт планировщика"""
    return _prompt_loader.load_prompt("planner")

def get_analyzer_prompt() -> str:
    """Возвращает промпт анализатора"""
    return _prompt_loader.load_prompt("analyzer")

def get_judge_prompt(**kwargs) -> str:
    """Возвращает промпт судьи с подстановкой переменных"""
    return _prompt_loader.format_prompt("judge", **kwargs)

def get_finalizer_prompt(**kwargs) -> str:
    """Возвращает промпт финализатора с подстановкой переменных"""
    return _prompt_loader.format_prompt("finalizer", **kwargs)

if __name__ == "__main__":
    # Тестирование
    loader = PromptLoader()
    
    print("=== Доступные промпты ===")
    available = loader.get_available_prompts()
    for prompt in available:
        print(f"- {prompt}")
    
    if available:
        print(f"\n=== Тест загрузки промпта '{available[0]}' ===")
        try:
            content = loader.load_prompt(available[0])
            print(f"Длина: {len(content)} символов")
            print(f"Первые 200 символов: {content[:200]}...")
        except Exception as e:
            print(f"Ошибка: {e}")
    
    print("\n=== Тест форматирования (judge) ===")
    try:
        formatted = loader.format_prompt("judge", 
                                       user_query="Тестовый запрос",
                                       plan_goal="Тестовая цель",
                                       remaining_plan_steps="[]",
                                       executor_output_json="{}",
                                       scratchpad_json="{}",
                                       history_log="[]")
        print(f"Форматирование успешно, длина: {len(formatted)} символов")
    except Exception as e:
        print(f"Ошибка форматирования: {e}") 