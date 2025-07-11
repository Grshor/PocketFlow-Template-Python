from flow import norma_agent_flow
import json
from utils.terminal_logger import start_terminal_logging, stop_terminal_logging
import debugpy


def main():
    debugpy.wait_for_client()
    
    """Основная функция для запуска агента нормативных документов с YAML-промптами"""
    
    # Начинаем логирование
    log_path = start_terminal_logging("norma_agent.log", "logs")
    
    print("🏗️ NormaGPT - Агент для работы с нормативной базой строительных документов")
    print("=" * 70)
    
    # Тестируем с первым вопросом из списка для отладки
    # user_query = "Имеется колонна диаметром 700 мм. Колонна находится на улице. Какую величину защитного слоя бетона принять для этой колонны? С учетом величины защитного слоя и минимального расстояния между стержнями, сколько получится разместить арматуры в такой колонне?"
    user_query = "Какие расчетные характеристики сопротивления бетона сжатию и растяжению для бетона класса B60?"
    print(f"Тестируем вопрос: {user_query}")
    
    # Инициализируем shared store
    shared = {
        "user_query": user_query,
        "status": "planning",
        "plan": None,
        "scratchpad": {},
        "execution_history": [],
        "step_results": {},
        "final_answer": None,
        "error": None
    }
    
    
    try:
        print(f"\n🚀 Начинаем обработку запроса...")
        
        # Запускаем агентный граф
        norma_agent_flow.run(shared)
        
        # Выводим результат
        print("\n" + "=" * 70)
        print("📋 РЕЗУЛЬТАТ:")
        print("=" * 70)
        
        if shared["status"] == "completed" and shared.get("final_answer"):
            print(shared["final_answer"])
            
            if shared.get("debug_summary"):
                print(f"\n🔍 Качество ответа: {shared['debug_summary'].get('overall_quality', 'неизвестно')}")
                print(f"🎯 Уверенность: {shared['debug_summary'].get('confidence_score', 0):.2f}")
        
        elif shared["status"] == "human_review_required":
            print("🚨 Требуется вмешательство специалиста")
            print(f"Причина: {shared.get('human_review_reason', 'Неизвестная причина')}")
        
        elif shared["status"] == "error":
            print(f"❌ Произошла ошибка: {shared.get('error', 'Неизвестная ошибка')}")
        
        else:
            print(f"⚠️ Неожиданный статус: {shared['status']}")
        
        # Отладочная информация
        print(f"\n🔧 Статус: {shared['status']}")
        print(f"📊 Выполнено шагов: {len(shared['execution_history'])}")
        
        if shared["execution_history"]:
            print("\n📈 История выполнения:")
            for i, step in enumerate(shared["execution_history"], 1):
                status_emoji = "✅" if step["status"] == "success" else "❌"
                print(f"  {i}. {status_emoji} {step['action']} -> {step['status']}")
        
        # Информация о YAML-промптах
        if shared.get("scratchpad"):
            print(f"\n🎯 Домен запроса: {shared['scratchpad'].get('query_domain', 'неизвестно')}")
            priority_docs = shared['scratchpad'].get('priority_documents', [])
            if priority_docs:
                print(f"📚 Приоритетные документы: {', '.join(priority_docs)}")
        
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Останавливаем логирование в любом случае
        stop_terminal_logging()
    
    print("\n👋 Работа завершена!")
    print("💡 YAML-промпты обеспечивают более структурированный и предсказуемый контроль над агентом")

if __name__ == "__main__":
    main()
