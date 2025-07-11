import sys
import os
from datetime import datetime
from contextlib import contextmanager

class TerminalLogger:
    """Класс для автоматического логирования вывода терминала в файл"""
    
    def __init__(self, log_file="terminal.log", log_dir="logs"):
        """
        Инициализирует логгер
        
        Args:
            log_file (str): Имя лог файла
            log_dir (str): Директория для логов
        """
        # Создаем директорию для логов если её нет
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Формируем полный путь к файлу с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(log_dir, f"{timestamp}_{log_file}")
        
        # Сохраняем оригинальные потоки
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Флаг активности логирования
        self.is_active = False
    
    def start_logging(self):
        """Начинает логирование в файл"""
        if self.is_active:
            return
        
        # Создаем файл для логирования
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        
        # Заменяем потоки на наши обёртки
        sys.stdout = TeeOutput(self.original_stdout, self.log_file)
        sys.stderr = TeeOutput(self.original_stderr, self.log_file)
        
        self.is_active = True
        
        # Записываем заголовок лога
        print(f"🚀 Начато логирование: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Файл лога: {self.log_path}")
        print("=" * 70)
    
    def stop_logging(self):
        """Останавливает логирование"""
        if not self.is_active:
            return
        
        print("=" * 70)
        print(f"🏁 Логирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Восстанавливаем оригинальные потоки
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Закрываем файл
        if hasattr(self, 'log_file'):
            self.log_file.close()
        
        self.is_active = False
        
        print(f"💾 Лог сохранён в: {self.log_path}")
    
    @contextmanager
    def logging_context(self):
        """Контекстный менеджер для временного логирования"""
        self.start_logging()
        try:
            yield self.log_path
        finally:
            self.stop_logging()


class TeeOutput:
    """Класс для дублирования вывода в консоль и файл одновременно"""
    
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file
    
    def write(self, text):
        """Записывает текст в оба потока"""
        # Записываем в оригинальный поток (консоль)
        self.original_stream.write(text)
        # Записываем в файл
        self.log_file.write(text)
        # Немедленно сбрасываем буферы
        self.original_stream.flush()
        self.log_file.flush()
    
    def flush(self):
        """Сбрасывает буферы обоих потоков"""
        self.original_stream.flush()
        self.log_file.flush()
    
    def __getattr__(self, name):
        """Перенаправляет все остальные атрибуты к оригинальному потоку"""
        return getattr(self.original_stream, name)


# Глобальный логгер для удобства использования
_global_logger = None

def start_terminal_logging(log_file="terminal.log", log_dir="logs"):
    """
    Начинает автоматическое логирование терминала
    
    Args:
        log_file (str): Имя лог файла
        log_dir (str): Директория для логов
    
    Returns:
        str: Путь к файлу лога
    """
    global _global_logger
    
    if _global_logger and _global_logger.is_active:
        print("⚠️ Логирование уже активно")
        return _global_logger.log_path
    
    _global_logger = TerminalLogger(log_file, log_dir)
    _global_logger.start_logging()
    return _global_logger.log_path

def stop_terminal_logging():
    """Останавливает автоматическое логирование терминала"""
    global _global_logger
    
    if _global_logger and _global_logger.is_active:
        _global_logger.stop_logging()
        return _global_logger.log_path
    else:
        print("⚠️ Логирование не активно")
        return None

def get_log_path():
    """Возвращает путь к текущему файлу лога"""
    global _global_logger
    
    if _global_logger:
        return _global_logger.log_path
    return None

# Декоратор для автологирования функций
def auto_log(log_file="function.log", log_dir="logs"):
    """
    Декоратор для автоматического логирования выполнения функции
    
    Args:
        log_file (str): Имя лог файла
        log_dir (str): Директория для логов
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = TerminalLogger(log_file, log_dir)
            with logger.logging_context():
                print(f"🎯 Запуск функции: {func.__name__}")
                if args or kwargs:
                    print(f"📋 Аргументы: args={args}, kwargs={kwargs}")
                
                try:
                    result = func(*args, **kwargs)
                    print(f"✅ Функция {func.__name__} выполнена успешно")
                    return result
                except Exception as e:
                    print(f"❌ Ошибка в функции {func.__name__}: {e}")
                    raise
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # Тест логирования
    print("Тестируем логирование...")
    
    log_path = start_terminal_logging("test.log")
    print("Это сообщение должно попасть в лог")
    print("И это тоже!")
    
    try:
        # Симулируем ошибку
        raise ValueError("Тестовая ошибка")
    except Exception as e:
        print(f"Поймали ошибку: {e}")
    
    stop_terminal_logging()
    print(f"Лог сохранён в: {log_path}") 