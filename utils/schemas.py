"""Pydantic схемы для валидации вывода агентов системы NormaGPT.

Данные схемы обеспечивают строгую типизацию и валидацию выходных данных
от LLM, предотвращая ошибки типа 'NoneType' object is not subscriptable.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# Основные схемы данных
class StructuredOutput(BaseModel):
    """Машиночитаемая структура данных из нормативных документов"""
    entity: str = Field(..., description="Название сущности (напр., 'Минимальный защитный слой')")
    value: Union[str, float, int] = Field(..., description="Значение параметра")
    units: Optional[str] = Field(None, description="Единицы измерения")
    variable_name: Optional[str] = Field(None, description="Имя переменной для расчетов")
    source_reference: str = Field(..., description="Ссылка на источник (СП, ГОСТ, таблица)")
    conditions: Optional[List[str]] = Field(None, description="Условия применения")

class SearchHypothesis(BaseModel):
    """Гипотеза для поиска в документах"""
    hypothesis: str = Field(..., description="Описание проверяемой гипотезы")
    keywords: List[str] = Field(..., description="Ключевые слова для поиска")
    expected_documents: List[str] = Field(..., description="Ожидаемые документы")

class PlanStep(BaseModel):
    """Шаг плана выполнения"""
    step_number: int = Field(..., description="Номер шага")
    reasoning: str = Field(..., description="Обоснование шага")
    action: str = Field(..., description="Описание действия")
    tool: str = Field(..., description="Используемый инструмент")
    input_variables: Optional[Dict[str, Any]] = Field(None, description="Входные переменные")
    expression: Optional[str] = Field(None, description="Математическое выражение для расчета")
    output_variable: str = Field(..., description="Имя выходной переменной")
    semantic_keywords: Optional[List[str]] = Field(None, description="Ключевые слова для поиска")
    expected_documents: Optional[List[str]] = Field(None, description="Ожидаемые документы")
    validation_criteria: Optional[str] = Field(None, description="Критерии валидации результата")

# Схемы для планировщика
class PlannerOutput(BaseModel):
    """Выходные данные планировщика"""
    initial_scratchpad: Dict[str, Any] = Field(..., description="Начальная рабочая область")
    context_analysis: Dict[str, Any] = Field(..., description="Анализ контекста запроса")
    plan: Dict[str, Any] = Field(..., description="План выполнения")
    debug: Optional[Dict[str, Any]] = Field(None, description="Отладочная информация")

# Схемы для исполнителя/анализатора
class StatusEnum(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"

class ErrorCodeEnum(str, Enum):
    IMAGE_QUALITY_LOW = "IMAGE_QUALITY_LOW"
    TEXT_FOUND_BUT_IRRELEVANT = "TEXT_FOUND_BUT_IRRELEVANT"
    AMBIGUOUS_INFO = "AMBIGUOUS_INFO"
    INFO_NOT_FOUND = "INFO_NOT_FOUND"
    NO_IMAGES_PROVIDED = "NO_IMAGES_PROVIDED"
    INVALID_INPUT = "INVALID_INPUT"

class AnalyzerOutput(BaseModel):
    """Выходные данные анализатора документов"""
    status: StatusEnum = Field(..., description="Статус выполнения")
    error_code: Optional[ErrorCodeEnum] = Field(None, description="Код ошибки")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    input_validation: Optional[Dict[str, Any]] = Field(None, description="Валидация входных данных")
    output: Optional[Dict[str, Any]] = Field(None, description="Результат анализа")
    evaluation: Dict[str, Any] = Field(..., description="Оценка качества результата")
    recommendations_for_developer: Optional[List[str]] = Field(None, description="Рекомендации разработчику")

    @validator('output')
    def validate_output_for_success(cls, v, values):
        """Валидация: при успешном статусе output должен содержать structured_output"""
        if values.get('status') == StatusEnum.SUCCESS and v:
            if 'structured_output' not in v:
                raise ValueError("При статусе 'success' поле output должно содержать 'structured_output'")
        return v

# Схемы для судьи
class DecisionEnum(str, Enum):
    CONTINUE = "CONTINUE"
    REPLAN = "REPLAN"
    FINALIZE = "FINALIZE"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"

class ReplanStrategyEnum(str, Enum):
    REFINE_AND_RESTRICT_SEARCH = "REFINE_AND_RESTRICT_SEARCH"
    CHANGE_KEYWORDS = "CHANGE_KEYWORDS"
    FORM_NEW_HYPOTHESIS = "FORM_NEW_HYPOTHESIS"
    FORM_CALCULATION_STEP = "FORM_CALCULATION_STEP"

class UpdateActionEnum(str, Enum):
    UPDATE = "UPDATE"
    REPLACE = "REPLACE"
    APPEND = "APPEND"

class JudgeOutput(BaseModel):
    """Выходные данные судьи"""
    decision: DecisionEnum = Field(..., description="Принятое решение")
    reasoning: str = Field(..., description="Обоснование решения")
    state_analysis: Dict[str, Any] = Field(..., description="Анализ состояния")
    replan_instructions: Optional[Dict[str, Any]] = Field(None, description="Инструкции для перепланировки")
    human_review_request: Optional[str] = Field(None, description="Запрос на человеческий контроль")
    updated_scratchpad: Optional[Dict[str, Any]] = Field(None, description="Обновления рабочей области")

    @validator('replan_instructions')
    def validate_replan_instructions(cls, v, values):
        """Валидация: при REPLAN должны быть инструкции"""
        if values.get('decision') == DecisionEnum.REPLAN and not v:
            raise ValueError("При решении 'REPLAN' должны быть указаны 'replan_instructions'")
        return v

# Схемы для финализатора  
class FinalizerOutput(BaseModel):
    """Выходные данные финализатора"""
    final_response: Dict[str, Any] = Field(..., description="Финальный ответ пользователю")

class CalculateInput(BaseModel):
    """Входные данные для инструмента calculate"""
    input_variables: Dict[str, Any] = Field(..., description="Переменные для расчета")
    expression: str = Field(..., description="Математическое выражение")
    output_variable: str = Field(..., description="Имя выходной переменной")

class CalculateOutput(BaseModel):
    """Выходные данные инструмента calculate"""
    status: StatusEnum = Field(..., description="Статус выполнения")
    result: Optional[Union[float, int, str]] = Field(None, description="Результат вычисления")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    calculation_steps: Optional[List[str]] = Field(None, description="Шаги вычисления") 