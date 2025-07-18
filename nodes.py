from pocketflow import Node
from utils.call_llm import call_llm
from utils.search_documents import search_documents, search_documents_with_images
from utils.parse_yaml import parse_yaml_response
from utils.prompt_loader import (
    get_planner_prompt, 
    get_analyzer_prompt, 
    get_judge_prompt, 
    get_finalizer_prompt
)
from utils.schemas import AnalyzerOutput, JudgeOutput, FinalizerOutput
from utils.calculate import calculate
import json
import re
from agent_debug.decorators import recordable_node

class PlannerNode(Node):
    """Создает план поиска на основе запроса пользователя с использованием YAML-промпта"""
    
    @recordable_node
    def prep(self, shared):
        return shared["user_query"]
    
    @recordable_node
    def exec(self, user_query):
        # Используем YAML-промпт планировщика
        system_prompt = get_planner_prompt()
        print(f"⏳ Отправляем запрос планировщику LLM...")
        response = call_llm(user_query, system_prompt)
        print(f"✅ Получен ответ от планировщика LLM")
        
        print(f"🔍 ОТЛАДКА: Ответ планировщика:")
        print(f"==== RAW RESPONSE ====")
        print(response)
        print(f"==== END RAW RESPONSE ====")
        
        parsed = parse_yaml_response(response)
        if "error" not in parsed:
            print(f"✅ ОТЛАДКА: Все поля успешно спаршены")
        else:
            print(f"❌ ОТЛАДКА: Ошибка парсинга YAML: {parsed.get('error', 'Неизвестная ошибка')}")
        
        return parsed
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        # Проверяем что exec_res не None
        if exec_res is None:
            shared["status"] = "error"
            shared["error"] = "Планировщик вернул пустой ответ. Возможно, проблема с LLM или парсингом YAML."
            return "error"
        
        if "error" in exec_res:
            shared["status"] = "error"
            shared["error"] = f"Ошибка планирования: {exec_res['error']}"
            return "error"
        
        # Проверяем наличие обязательных полей
        if "plan" not in exec_res:
            shared["status"] = "error"
            shared["error"] = f"Отсутствует поле 'plan' в ответе планировщика. Получено: {list(exec_res.keys())}"
            return "error"
        
        # Сохраняем план и начальные данные
        shared["plan"] = exec_res["plan"]
        shared["scratchpad"] = exec_res.get("initial_scratchpad", {})
        shared["context_analysis"] = exec_res.get("context_analysis", {})
        shared["plan"]["current_step_index"] = 0
        shared["status"] = "executing"
        shared["execution_history"] = []
        shared["step_results"] = {}
        
        print(f"📋 План создан: {exec_res['plan'].get('goal', 'Неизвестная цель')}")
        print(f"🎯 Шагов в плане: {len(exec_res['plan'].get('steps', []))}")
        
        return "execute"

class ExecutorNode(Node):
    """Выполняет текущий шаг плана с поддержкой Vision API для анализа изображений"""
    
    @recordable_node
    def prep(self, shared):
        plan = shared["plan"]
        current_index = plan["current_step_index"]
        
        if current_index >= len(plan["steps"]):
            return None  # Все шаги выполнены
            
        current_step = plan["steps"][current_index]
        
        # Добавляем step_results для calculate операций
        current_step["step_results"] = shared.get("step_results", {})
        
        # Добавляем user_query для извлечения параметров из запроса
        current_step["user_query"] = shared.get("user_query", "")
        
        return current_step
    
    @recordable_node
    def exec(self, current_step):
        if current_step is None:
            return {"status": "completed", "message": "Все шаги выполнены"}
        
        print(f"🔄 Выполняем шаг с Vision API {current_step['step_number']}: {current_step['action']}")
        
        # Выполняем поиск документов с изображениями
        if current_step["tool"] == "search_documents":
            
            # Извлекаем параметры поиска
            semantic_keywords = current_step["semantic_keywords"]
            expected_documents = current_step.get("expected_documents", [])
            
            print(f"🔍 Поиск с изображениями: {semantic_keywords}")
            
            # Выполняем поиск с изображениями
            documents = search_documents_with_images(
                semantic_keywords, 
                expected_documents, 
                include_images=True,
                hits=3
            )
            
            if documents is None:
                print(f"❌ Поиск с изображениями не дал результатов")
                return {
                    "status": "failure",
                    "error_code": "SEARCH_FAILED",
                    "error_message": "Поиск документов с изображениями не дал результатов",
                    "output": {"data": "Документы не найдены в базе"}
                }
            
            print(f"🔍 Найдено {len(documents)} документов")
            
            # Собираем только изображения и источники для анализатора
            vision_messages = []
            sources_info = []
            images_count = 0
            
            for doc in documents:
                # Добавляем изображение в Vision API формате если есть
                if doc.get("vision_content"):
                    vision_messages.extend(doc["vision_content"])
                    sources_info.append({
                        "source_document": doc["source_document"]
                    })
                    images_count += 1
            
            print(f"🖼️ Отправляем {images_count} изображений в анализатор")
            
            # Анализируем с помощью Vision API - только изображения + источники
            system_prompt = get_analyzer_prompt()
            
            # Пользовательский промпт содержит только вопрос и информацию об источниках
            import yaml
            sources_yaml = yaml.dump(sources_info, allow_unicode=True, default_flow_style=False)
            user_prompt = f"""Задача: {current_step.get("action", "Проанализируйте изображения документов")}

Источники изображений:
{sources_yaml}

Проанализируйте изображения документов и ответьте на поставленную задачу."""
            
            # Retry логика для Vision анализатора
            max_retries = 3
            for attempt in range(max_retries):
                print(f"⏳ Отправляем запрос Vision анализатору LLM (попытка {attempt + 1}/{max_retries})...")
                response = call_llm(
                    user_prompt, 
                    system_prompt, 
                    task_type="analyzer",
                    vision_content=vision_messages
                )
                print(f"✅ Получен ответ от Vision анализатора LLM")
                
                print(f"📝 Ответ анализатора:")
                print(response)
                
                result = parse_yaml_response(response)
                
                # Если парсинг прошел успешно (нет поля error), выходим из цикла
                if "error" not in result:
                    break
                    
                print(f"❌ Попытка {attempt + 1}: Не удалось распарсить YAML ответ")
                if attempt < max_retries - 1:
                    print(f"🔄 Повторяем попытку...")
            
            # Если все попытки неудачны
            if "error" in result:
                return {
                    "status": "failure",
                    "error_code": "PARSE_FAILED",
                    "error_message": f"Не удалось распарсить ответ Vision анализатора после {max_retries} попыток: {result.get('error', 'Неизвестная ошибка')}",
                    "output": {"data": "Ошибка анализа изображений документов"}
                }
            
            # Безопасное извлечение данных с проверкой типов
            if "error" not in result and result.get("status") == "success":
                result_output = result.get("output", {})
                
                # Проверяем что output является словарем
                if isinstance(result_output, dict):
                    adapted_result = {
                        "status": "success",
                        "output": {
                            "data": result_output.get("data", ""),
                            "structured_output": result_output.get("structured_output", []),
                            "source": result_output.get("source", {}),
                            "evaluation": result.get("evaluation", {}) if isinstance(result, dict) else {}
                        }
                    }
                else:
                    # Если output не словарь, используем как строку
                    adapted_result = {
                        "status": "success",
                        "output": {
                            "data": str(result_output),
                            "source": {},
                            "evaluation": result.get("evaluation", {})
                        }
                    }
                
                print(f"✅ Vision анализ выполнен успешно")
                return adapted_result
            
            print(f"❌ Ошибка Vision анализа")
            return result
        
        elif current_step["tool"] == "calculate":
            # Выполняем математическое вычисление
            from utils.calculate import calculate
            import math
            
            print(f"🧮 Выполняем математическое вычисление")
            
            # Логика извлечения значений из step_results предыдущих шагов и input_variables
            input_variables = current_step.get("input_variables", {})
            print(f"📊 Требуемые переменные: {input_variables}")
            
            step_results = current_step.get("step_results", {})
            user_query = current_step.get("user_query", "")
            
            # Создаем контекст для вычислений из всех доступных данных
            calculation_context = {}
            
            # Обрабатываем input_variables (это словарь, а не список)
            for var_name, var_value in input_variables.items():
                if isinstance(var_value, (int, float)):
                    calculation_context[var_name] = var_value
                elif isinstance(var_value, str):
                    # Если это ссылка на результат предыдущего шага
                    if var_value.startswith("{") and var_value.endswith("}"):
                        # Обрабатываем ссылки типа {step_1.structured_output.value}
                        ref = var_value.strip("{}")
                        print(f"🔗 Обрабатываем ссылку: {ref}")
                        
                        # Извлекаем значение из результатов предыдущих шагов
                        if ref.startswith("step_") and ".structured_output.value" in ref:
                            step_match = re.match(r'step_(\d+)\.structured_output\.value', ref)
                            if step_match:
                                step_num = int(step_match.group(1))
                                step_key = f"step_{step_num}"
                                
                                if step_key in step_results:
                                    structured_output = step_results[step_key].get("output", {}).get("structured_output", [])
                                    if isinstance(structured_output, list) and len(structured_output) > 0:
                                        value = structured_output[0].get("value")
                                        if isinstance(value, (int, float)):
                                            calculation_context[var_name] = value
                                            print(f"✅ Извлечено значение: {var_name} = {value}")
                                            continue
                        
                        # Если не удалось извлечь, ставим 0
                        calculation_context[var_name] = 0
                        print(f"⚠️ Не удалось извлечь значение для {var_name}, используем 0")
                    else:
                        # Пытаемся преобразовать строку в число
                        try:
                            calculation_context[var_name] = float(var_value)
                        except ValueError:
                            calculation_context[var_name] = 0
            
            # Извлекаем числа из пользовательского запроса
            user_numbers = re.findall(r'\d+(?:\.\d+)?', user_query)
            for i, num in enumerate(user_numbers):
                calculation_context[f"user_value_{i}"] = float(num)
            
            # Извлекаем числа из результатов предыдущих шагов
            for step_id, result in step_results.items():
                step_data = result.get("output", {}).get("data", "")
                if isinstance(step_data, str):
                    numbers = re.findall(r'\d+(?:\.\d+)?', step_data)
                    for i, num in enumerate(numbers):
                        calculation_context[f"{step_id}_value_{i}"] = float(num)
                # Новый блок: добавляем structured_output, если есть
                structured_items = result.get("output", {}).get("structured_output", [])
                if isinstance(structured_items, list):
                    for item in structured_items:
                        var_name = item.get("variable_name") or item.get("entity")
                        value = item.get("value")
                        if var_name and isinstance(value, (int, float)):
                            calculation_context[var_name] = value
            
            print(f"📊 Контекст вычислений: {calculation_context}")
            
            # Получаем выражение для вычисления
            expression = current_step.get("expression", "")
            formula = current_step.get("formula", "")
            
            # Используем formula если есть, иначе expression
            calc_expression = formula if formula else expression
            
            if not calc_expression:
                # Если нет явного выражения, пытаемся найти формулу в результатах предыдущих шагов
                print("🔍 Ищем формулы в результатах предыдущих шагов...")
                
                # Ищем формулы в текстах предыдущих шагов
                formula_patterns = [
                    r'([А-Яа-я_]+)\s*=\s*([^=\n]+)',  # Формула вида A = B * C
                    r'формула[:\s]*([^.\n]+)',        # "формула: выражение"
                    r'расчет[:\s]*([^.\n]+)',         # "расчет: выражение"
                    r'([А-Яа-я_]+)\s*рассчитывается\s*по\s*формуле[:\s]*([^.\n]+)',
                ]
                
                found_formulas = []
                for step_id, result in step_results.items():
                    step_data = result.get("output", {}).get("data", "")
                    if isinstance(step_data, str):
                        for pattern in formula_patterns:
                            matches = re.findall(pattern, step_data, re.IGNORECASE)
                            for match in matches:
                                if isinstance(match, tuple) and len(match) == 2:
                                    formula_name, formula_expr = match
                                    found_formulas.append({
                                        "step": step_id,
                                        "name": formula_name.strip(),
                                        "expression": formula_expr.strip()
                                    })
                                    print(f"📐 Найдена формула в {step_id}: {formula_name} = {formula_expr}")
                
                # Если найдены формулы, используем первую подходящую
                if found_formulas:
                    calc_expression = found_formulas[0]["expression"]
                    print(f"📐 Используем найденную формулу: {calc_expression}")
                
                # Если все еще нет выражения, пытаемся создать простое вычисление
                elif len(calculation_context) >= 2:
                    values = list(calculation_context.values())
                    # Простая операция с первыми двумя числами
                    calc_expression = f"{values[0]} + {values[1]}"
                    print(f"📐 Создаем простое выражение: {calc_expression}")
                else:
                    return {
                        "status": "failure", 
                        "error_code": "NO_EXPRESSION",
                        "error_message": "Не указано выражение для вычисления и не найдено формул в предыдущих шагах",
                        "output": {"data": "Ошибка: отсутствует математическое выражение"}
                    }
            
            print(f"📐 Выражение для вычисления: {calc_expression}")
            
            # Заменяем переменные в выражении на значения (сортируем по длине имени переменной в убывающем порядке)
            final_expression = calc_expression
            sorted_vars = sorted(calculation_context.items(), key=lambda x: len(x[0]), reverse=True)
            for var_name, var_value in sorted_vars:
                final_expression = final_expression.replace(var_name, str(var_value))
            
            # Заменяем π на math.pi
            final_expression = final_expression.replace("π", str(math.pi))
            final_expression = final_expression.replace("pi", str(math.pi))
            
            print(f"📐 Финальное выражение: {final_expression}")
            
            # Выполняем вычисление
            calc_result = calculate(
                input_variables={},  # Переменные уже подставлены в выражение
                expression=final_expression,
                output_variable=current_step.get("output_variable", "result")
            )
            
            if calc_result.get("status") == "success":
                result_value = calc_result.get("result")
                return {
                    "status": "success",
                    "output": {
                        "data": f"Результат вычисления: {result_value}\n\nВыражение: {calc_expression}\nПодстановка: {final_expression}",
                        "structured_output": [{
                            "entity": current_step.get("output_variable", "result"),
                            "value": result_value,
                            "variable_name": current_step.get("output_variable", "result"),
                            "source_reference": "Вычислено"
                        }],
                        "source": {
                            "tool": "calculate", 
                            "expression": calc_expression,
                            "final_expression": final_expression,
                            "context": calculation_context
                        }
                    }
                }
            else:
                return {
                    "status": "failure",
                    "error_message": calc_result.get("error_message", "Ошибка расчета"),
                    "output": {
                        "data": f"Ошибка вычисления: {calc_result.get('error_message', 'Неизвестная ошибка')}"
                    }
                }
            
        else:
            return {
                "status": "failure",
                "error_code": "UNSUPPORTED_TOOL",
                "error_message": f"Инструмент '{current_step['tool']}' не поддерживается",
                "output": {"data": "Неподдерживаемый инструмент"}
            }
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        plan = shared["plan"]
        current_index = plan["current_step_index"]
        
        if prep_res is None:
            shared["status"] = "judging_final"
            return "judge"
        
        # Проверяем что exec_res не None
        if exec_res is None:
            exec_res = {
                "status": "failure",
                "error": "Executor вернул None",
                "output": {"data": "Ошибка выполнения"}
            }
        
        # Проверяем тип ошибки - если это ошибка парсинга после всех retry, переходим сразу к следующему шагу
        if (isinstance(exec_res, dict) and 
            exec_res.get("status") == "failure" and 
            exec_res.get("error_code") == "PARSE_FAILED" and
            "после" in str(exec_res.get("error_message", ""))):
            print(f"❌ Критическая ошибка парсинга Vision анализатора после всех попыток - пропускаем судью")
            # Переходим к следующему шагу
            plan["current_step_index"] += 1
            step_id = f"step_{current_index + 1}"
            shared["step_results"][step_id] = exec_res
            
            shared["execution_history"].append({
                "step_number": current_index + 1,
                "action": prep_res.get("action", "Неизвестное действие") if prep_res else "Неизвестное действие",
                "status": "failed_parse",
                "result_summary": f"Ошибка парсинга Vision: {exec_res.get('error_message', 'Неизвестная ошибка')}"
            })
            
            if plan["current_step_index"] >= len(plan["steps"]):
                return "judge"
            else:
                return "execute"
        
        # Сохраняем результат шага
        step_id = f"step_{current_index + 1}"
        shared["step_results"][step_id] = exec_res
        
        # Добавляем в историю выполнения с безопасной проверкой
        result_summary = "Нет результата"
        if (exec_res and 
            isinstance(exec_res.get("output"), dict) and 
            exec_res["output"].get("data")):
            result_summary = str(exec_res["output"]["data"])[:100] + "..."
        
        shared["execution_history"].append({
            "step_number": current_index + 1,
            "action": prep_res.get("action", "Неизвестное действие"),
            "status": exec_res.get("status", "unknown") if exec_res else "unknown",
            "result_summary": result_summary
        })
        
        if exec_res and exec_res.get("status") == "completed":
            return "judge"
        elif exec_res and exec_res.get("status") == "success":
            # Переходим к следующему шагу
            plan["current_step_index"] += 1
            if plan["current_step_index"] >= len(plan["steps"]):
                return "judge"
            else:
                return "execute"
        else:
            # Переходим к судье для оценки результата
            shared["status"] = "judging"
            return "judge"

class JudgeNode(Node):
    """Оценивает результат и принимает решение о следующем действии с использованием YAML-промпта"""
    
    @recordable_node
    def prep(self, shared):
        current_index = shared["plan"]["current_step_index"]
        
        # Подготавливаем данные для судьи
        judge_input = {
            "user_query": shared["user_query"],
            "plan_goal": shared["plan"]["goal"],
            "remaining_plan_steps": shared["plan"]["steps"][current_index + 1:],
            "last_step_result": shared["step_results"].get(f"step_{current_index + 1}", {}),
            "scratchpad": shared["scratchpad"],
            "execution_history": shared["execution_history"]
        }
        
        return judge_input
    
    @recordable_node
    def exec(self, judge_input):
        # Используем YAML-промпт судьи с подстановкой переменных
        import yaml
        system_prompt = get_judge_prompt(
            user_query=judge_input["user_query"],
            plan_goal=judge_input["plan_goal"],
            remaining_plan_steps=yaml.dump(judge_input["remaining_plan_steps"], allow_unicode=True, default_flow_style=False),
            executor_output_json=yaml.dump(judge_input["last_step_result"], allow_unicode=True, default_flow_style=False),
            scratchpad_json=yaml.dump(judge_input["scratchpad"], allow_unicode=True, default_flow_style=False),
            history_log=yaml.dump(judge_input["execution_history"], allow_unicode=True, default_flow_style=False)
        )
        
        print(f"🔍 ОТЛАДКА СУДЬИ: Вызываем LLM с промптом длиной {len(system_prompt)} символов")
        
        # Retry логика для судьи
        max_retries = 3
        for attempt in range(max_retries):
            print(f"⏳ Отправляем запрос судье LLM (попытка {attempt + 1}/{max_retries})...")
            response = call_llm("Проанализируй ситуацию и прими решение.", system_prompt)
            print(f"✅ Получен ответ от судьи LLM")
            print(f"🔍 ОТЛАДКА СУДЬИ: Получен ответ от LLM:")
            print(f"==== RAW JUDGE RESPONSE ====")
            print(response)
            print(f"==== END RAW JUDGE RESPONSE ====")
            
            parsed = parse_yaml_response(response)
            
            # Если парсинг прошел успешно (нет поля error), выходим из цикла
            if "error" not in parsed:
                print(f"✅ ОТЛАДКА СУДЬИ: Все поля успешно спаршены")
                return parsed
                
            print(f"❌ Попытка {attempt + 1}: Ошибка парсинга YAML: {parsed.get('error', 'Неизвестная ошибка')}")
            if attempt < max_retries - 1:
                print(f"🔄 Повторяем попытку...")
        
        # Если все попытки неудачны, возвращаем fallback решение
        print(f"❌ ОТЛАДКА СУДЬИ: Все попытки неудачны после {max_retries} попыток")
        print("🔄 Используем fallback решение: REPLAN")
        
        # Возвращаем fallback решение о перепланировании
        return {
            "decision": "REPLAN",
            "reasoning": f"Не удалось получить валидный YAML ответ от судьи после {max_retries} попыток. Требуется перепланирование.",
            "state_analysis": {
                "last_step_status": "unknown",
                "source_relevance_score": 0.5,
                "consistency_with_context_score": 0.5,
                "contradiction_details": None,
                "is_loop_detected": False
            },
            "replan_instructions": {
                "strategy": "RETRY_CURRENT_APPROACH",
                "details": "Повторить текущий подход с уточненными параметрами поиска"
            },
            "human_review_request": None,
            "updated_scratchpad": {
                "action": "NO_UPDATE",
                "data": {}
            }
        }
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        # Проверяем что exec_res не None
        if exec_res is None:
            shared["status"] = "error"
            shared["error"] = "Ошибка принятия решения: Судья вернул None"
            return "error"
        
        # Проверяем наличие ошибки в ответе
        if exec_res.get("error"):
            shared["status"] = "error"
            shared["error"] = f"Ошибка принятия решения: {exec_res['error']}"
            return "error"
        
        # Проверяем наличие decision
        if "decision" not in exec_res:
            shared["status"] = "error"
            shared["error"] = f"Ошибка принятия решения: Отсутствует поле 'decision' в ответе судьи. Получено: {list(exec_res.keys())}"
            return "error"
        
        decision = exec_res["decision"]
        print(f"⚖️ Решение судьи: {decision}")
        print(f"💭 Обоснование: {exec_res['reasoning']}")
        
        # Обновляем scratchpad если нужно
        if (isinstance(exec_res, dict) and 
            "updated_scratchpad" in exec_res and 
            isinstance(exec_res["updated_scratchpad"], dict) and
            exec_res["updated_scratchpad"].get("action") == "UPDATE"):
            scratchpad_data = exec_res["updated_scratchpad"].get("data", {})
            if isinstance(scratchpad_data, dict):
                shared["scratchpad"].update(scratchpad_data)
        
        if decision == "CONTINUE":
            # Переходим к следующему шагу
            shared["plan"]["current_step_index"] += 1
            shared["status"] = "executing"
            return "execute"
            
        elif decision == "REPLAN":
            # Нужно перепланировать
            shared["status"] = "planning"
            # TODO: В будущем можно добавить логику для улучшения планирования на основе replan_instructions
            return "plan"
            
        elif decision == "FINALIZE":
            # Готовы финализировать ответ
            shared["status"] = "finalizing"
            return "finalize"
            
        elif decision == "REQUEST_HUMAN_REVIEW":
            # Требуется вмешательство человека
            shared["status"] = "human_review_required"
            shared["human_review_reason"] = exec_res.get("reasoning", "Неизвестная причина") if isinstance(exec_res, dict) else "Неизвестная причина"
            return "human_review"
        
        else:
            shared["status"] = "error"
            shared["error"] = f"Неизвестное решение судьи: {decision}"
            return "error"

class FinalizerNode(Node):
    """Создает итоговый ответ пользователю с использованием YAML-промпта"""
    
    @recordable_node
    def prep(self, shared):
        # Собираем все успешные результаты
        successful_steps = {}
        for step_id, result in shared["step_results"].items():
            if result.get("status") == "success":
                successful_steps[step_id] = result["output"]
        
        finalizer_input = {
            "user_query": shared["user_query"],
            "overall_goal": shared["plan"]["goal"],
            "summary_of_successful_steps": successful_steps
        }
        
        return finalizer_input
    
    @recordable_node
    def exec(self, finalizer_input):
        # Используем YAML-промпт финализатора с подстановкой переменных
        import yaml
        system_prompt = get_finalizer_prompt(
            user_query=finalizer_input["user_query"],
            overall_goal=finalizer_input["overall_goal"],
            summary_of_successful_steps=yaml.dump(finalizer_input["summary_of_successful_steps"], allow_unicode=True, default_flow_style=False)
        )
        
        # Retry логика для финализатора
        max_retries = 3
        for attempt in range(max_retries):
            print(f"⏳ Отправляем запрос финализатору LLM (попытка {attempt + 1}/{max_retries})...")
            response = call_llm("Создай финальный ответ пользователю.", system_prompt)
            print(f"✅ Получен ответ от финализатора LLM")
            print(f"🔍 ОТЛАДКА ФИНАЛИЗАТОРА: Получен ответ от LLM:")
            print(f"==== RAW FINALIZER RESPONSE ====")
            print(response)
            print(f"==== END RAW FINALIZER RESPONSE ====")
            
            parsed = parse_yaml_response(response)
            
            # Если парсинг прошел успешно (нет поля error), выходим из цикла
            if "error" not in parsed:
                print(f"✅ ОТЛАДКА ФИНАЛИЗАТОРА: YAML успешно спаршен")
                final_response = parsed.get("final_response")
                if final_response and isinstance(final_response, dict) and "analysis" in final_response:
                    print(f"📝 ОТЛАДКА ФИНАЛИЗАТОРА: Длина анализа: {len(final_response['analysis'])} символов")
                return parsed
                
            print(f"❌ Попытка {attempt + 1}: Ошибка парсинга YAML: {parsed.get('error', 'Неизвестная ошибка')}")
            if attempt < max_retries - 1:
                print(f"🔄 Повторяем попытку...")
        
        # Если все попытки неудачны, возвращаем последний результат с ошибкой
        print(f"❌ ОТЛАДКА ФИНАЛИЗАТОРА: Все попытки неудачны после {max_retries} попыток")
        return parsed
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["status"] = "error"
            shared["error"] = f"Ошибка финализации: {exec_res['error']}"
            return "error"
        
        # Проверяем наличие поля final_response
        if "final_response" not in exec_res:
            shared["status"] = "error"
            shared["error"] = f"Ошибка финализации: Отсутствует поле 'final_response' в ответе финализатора. Получено: {list(exec_res.keys())}"
            return "error"
        
        # Извлекаем данные из final_response
        final_response = exec_res["final_response"]
        analysis_text = final_response.get("analysis", "Ответ не найден")
        
        # Обрабатываем markdown блоки кода для корректного отображения
        if isinstance(analysis_text, str):
            # Заменяем тройные бэктики на простые для избежания конфликтов
            analysis_text = analysis_text.replace("```", "")
        
        shared["final_answer"] = analysis_text
        shared["sources"] = final_response.get("sources", [])
        shared["limitations"] = final_response.get("limitations", [])
        shared["recommendations"] = final_response.get("recommendations", [])
        shared["status"] = "completed"
        
        print("✅ Итоговый ответ готов!")
        return "completed"

class HumanReviewNode(Node):
    """Узел для случаев, когда требуется вмешательство человека"""
    
    @recordable_node
    def prep(self, shared):
        return {
            "reason": shared.get("human_review_reason", "Неизвестная причина"),
            "history": shared["execution_history"],
            "current_data": shared["step_results"]
        }
    
    @recordable_node
    def exec(self, prep_res):
        print("\n🚨 ТРЕБУЕТСЯ ВМЕШАТЕЛЬСТВО ЧЕЛОВЕКА 🚨")
        print(f"Причина: {prep_res['reason']}")
        print("\nИстория выполнения:")
        for entry in prep_res["history"]:
            print(f"  - Шаг {entry['step_number']}: {entry['action']} -> {entry['status']}")
        
        # В реальной системе здесь можно добавить интерфейс для взаимодействия с человеком
        # Пока просто возвращаем статус
        return {"status": "human_review_requested", "data": prep_res}
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        shared["human_review_result"] = exec_res
        return "completed"

class ErrorNode(Node):
    """Узел для обработки ошибок"""
    
    @recordable_node
    def prep(self, shared):
        return shared.get("error", "Неизвестная ошибка")
    
    @recordable_node
    def exec(self, error_msg):
        print(f"❌ ОШИБКА: {error_msg}")
        return {"error_handled": True, "error_message": error_msg}
    
    @recordable_node
    def post(self, shared, prep_res, exec_res):
        shared["error_handled"] = True
        return "completed"