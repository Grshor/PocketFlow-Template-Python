from pocketflow import Flow
from nodes import (
    PlannerNode, ExecutorNode, JudgeNode, 
    FinalizerNode, HumanReviewNode, ErrorNode
)

def create_norma_agent_flow():
    """Создает и возвращает агентный граф для работы с нормативными документами"""
    
    # Создаем узлы
    planner = PlannerNode()
    executor = ExecutorNode()
    judge = JudgeNode()
    finalizer = FinalizerNode()
    human_review = HumanReviewNode()
    error_handler = ErrorNode()
    
    # Настраиваем переходы между узлами
    # Планировщик -> Исполнитель или Ошибка
    planner - "execute" >> executor
    planner - "error" >> error_handler
    
    # Исполнитель -> Судья
    executor - "judge" >> judge
    executor - "execute" >> executor   # Продолжить выполнение следующего шага
    
    # Судья принимает решения
    judge - "execute" >> executor      # Продолжить выполнение
    judge - "plan" >> planner         # Перепланировать
    judge - "finalize" >> finalizer   # Финализировать ответ
    judge - "human_review" >> human_review  # Требуется человек
    judge - "error" >> error_handler  # Ошибка
    
    # Финализатор завершает работу
    finalizer - "completed" >> None
    finalizer - "default" >> None
    
    # Остальные узлы также завершают работу
    human_review - "completed" >> None
    human_review - "default" >> None
    error_handler - "completed" >> None
    error_handler - "default" >> None
    
    # Создаем граф, начиная с планировщика
    return Flow(start=planner)

# Создаем основной граф
norma_agent_flow = create_norma_agent_flow()