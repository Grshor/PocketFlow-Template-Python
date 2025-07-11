"""
Модуль для выполнения математических вычислений.

Пример использования:
from utils.calculate import calculate

result = calculate("2 + 2 * 3")
print(result)  # Результат: 8
"""

import logging
import re
import math
from typing import Dict, Any, Union
from utils.schemas import CalculateInput, CalculateOutput, StatusEnum

logger = logging.getLogger(__name__)


def calculate(input_variables: Dict[str, Any], expression: str, output_variable: str) -> Dict[str, Any]:
    """
    Выполняет математические вычисления на основе переданных переменных и выражения.
    
    Args:
        input_variables: Словарь с переменными для подстановки в формулу
        expression: Математическое выражение для вычисления
        output_variable: Имя выходной переменной
        
    Returns:
        Dict с результатом вычисления в формате CalculateOutput
    """
    try:
        # Валидация входных данных
        calc_input = CalculateInput(
            input_variables=input_variables,
            expression=expression,
            output_variable=output_variable
        )
        
        print(f"🧮 Начинаем расчет: {output_variable}")
        print(f"📊 Входные переменные: {input_variables}")
        print(f"📐 Выражение: {expression}")
        
        # Создаем локальный контекст для вычислений
        calc_context = {
            # Математические функции
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'sqrt': math.sqrt,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'pow': math.pow,
            'abs': abs,
            'min': min,
            'max': max,
            'floor': math.floor,
            'ceil': math.ceil,
            'round': round,
            # Константы
            'pi': math.pi,
            'e': math.e,
        }
        
        # Обрабатываем входные переменные
        processed_vars = {}
        calculation_steps = []
        
        for var_name, var_value in input_variables.items():
            if isinstance(var_value, str) and var_value.startswith('{') and var_value.endswith('}'):
                # Обработка ссылок на результаты предыдущих шагов
                # Например: "{step_1.structured_output.value}" -> значение из step_1
                calculation_steps.append(f"Переменная {var_name} ссылается на: {var_value}")
                # В реальной реализации здесь была бы логика извлечения значения
                # Пока что просто удаляем фигурные скобки как заглушка
                clean_value = var_value.strip('{}')
                calculation_steps.append(f"⚠️ Заглушка: {var_name} = {clean_value} (требуется реализация извлечения из контекста)")
                processed_vars[var_name] = 0  # Заглушка
            else:
                processed_vars[var_name] = float(var_value) if not isinstance(var_value, (int, float)) else var_value
                calculation_steps.append(f"Переменная {var_name} = {processed_vars[var_name]}")
        
        # Добавляем обработанные переменные в контекст
        calc_context.update(processed_vars)
        
        calculation_steps.append(f"Вычисляем: {expression}")
        
        # Выполняем вычисление
        result = eval(expression, {"__builtins__": {}}, calc_context)
        
        calculation_steps.append(f"Результат: {result}")
        
        print(f"✅ Расчет завершен: {output_variable} = {result}")
        
        # Возвращаем результат в формате CalculateOutput
        output = CalculateOutput(
            status=StatusEnum.SUCCESS,
            result=result,
            error_message=None,
            calculation_steps=calculation_steps
        )
        
        return output.dict()
        
    except ValueError as e:
        error_msg = f"Ошибка валидации входных данных: {str(e)}"
        print(f"❌ {error_msg}")
        return CalculateOutput(
            status=StatusEnum.FAILURE,
            result=None,
            error_message=error_msg,
            calculation_steps=None
        ).dict()
        
    except ZeroDivisionError as e:
        error_msg = f"Деление на ноль в выражении: {expression}"
        print(f"❌ {error_msg}")
        return CalculateOutput(
            status=StatusEnum.FAILURE,
            result=None,
            error_message=error_msg,
            calculation_steps=None
        ).dict()
        
    except NameError as e:
        error_msg = f"Неизвестная переменная в выражении: {str(e)}"
        print(f"❌ {error_msg}")
        return CalculateOutput(
            status=StatusEnum.FAILURE,
            result=None,
            error_message=error_msg,
            calculation_steps=None
        ).dict()
        
    except SyntaxError as e:
        error_msg = f"Синтаксическая ошибка в выражении: {str(e)}"
        print(f"❌ {error_msg}")
        return CalculateOutput(
            status=StatusEnum.FAILURE,
            result=None,
            error_message=error_msg,
            calculation_steps=None
        ).dict()
        
    except Exception as e:
        error_msg = f"Неожиданная ошибка при вычислении: {str(e)}"
        print(f"❌ {error_msg}")
        return CalculateOutput(
            status=StatusEnum.FAILURE,
            result=None,
            error_message=error_msg,
            calculation_steps=None
        ).dict()

def extract_step_value(step_reference: str, global_context: Dict[str, Any]) -> Union[float, int]:
    """
    Извлекает значение из результатов предыдущих шагов.
    
    Args:
        step_reference: Ссылка типа "step_1.structured_output.value"
        global_context: Глобальный контекст с результатами всех шагов
        
    Returns:
        Извлеченное значение
    """
    # Пример реализации для извлечения значений из контекста
    try:
        # Парсим ссылку типа "step_1.structured_output.value"
        match = re.match(r'step_(\d+)\.structured_output\.value', step_reference)
        if match:
            step_num = int(match.group(1))
            step_key = f"step_{step_num}"
            
            if step_key in global_context and 'structured_output' in global_context[step_key]:
                structured_data = global_context[step_key]['structured_output']
                if isinstance(structured_data, list) and len(structured_data) > 0:
                    return structured_data[0].get('value', 0)
                elif isinstance(structured_data, dict):
                    return structured_data.get('value', 0)
        
        # Если не удалось извлечь, возвращаем 0
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    # Тестирование
    test_cases = [
        {
            "input_variables": {"D": 700, "a": 40, "s_min": 25, "d_bar": 16},
            "expression": "floor(pi * (D - 2*a - d_bar) / (s_min + d_bar))",
            "output_variable": "max_rebar_count"
        },
        {
            "input_variables": {"L": 6000, "q": 15, "b": 300, "h": 500},
            "expression": "q * L * L / 8",
            "output_variable": "max_moment"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n=== ТЕСТ {i} ===")
        result = calculate(**test)
        print(f"Результат теста {i}: {result}") 