#!/usr/bin/env python3
"""
Скрипт для запуска приложения с автоматическим логированием
"""

import subprocess
import sys
from utils.terminal_logger import start_terminal_logging, stop_terminal_logging

def run_with_auto_logging(script_name="main.py", log_name=None):
    """
    Запускает Python скрипт с автоматическим логированием
    
    Args:
        script_name (str): Имя скрипта для запуска
        log_name (str): Имя лог файла (по умолчанию используется имя скрипта)
    """
    if log_name is None:
        log_name = script_name.replace('.py', '.log')
    
    print(f"🚀 Запуск {script_name} с логированием...")
    
    # Начинаем логирование
    log_path = start_terminal_logging(log_name, "logs")
    
    try:
        # Запускаем скрипт как подпроцесс
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print(f"✅ Скрипт {script_name} выполнен успешно")
        else:
            print(f"❌ Скрипт {script_name} завершился с ошибкой (код: {result.returncode})")
            
    except KeyboardInterrupt:
        print(f"\n🛑 Выполнение прервано пользователем")
    except Exception as e:
        print(f"💥 Ошибка при запуске: {e}")
    finally:
        # Останавливаем логирование
        final_log_path = stop_terminal_logging()
        if final_log_path:
            print(f"📁 Полный лог сохранён в: {final_log_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        script_to_run = sys.argv[1]
        log_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        script_to_run = "main.py"
        log_file = None
    
    run_with_auto_logging(script_to_run, log_file) 