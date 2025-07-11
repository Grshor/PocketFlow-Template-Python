"""
Модуль для поиска документов в нормативной базе через Vespa с поддержкой изображений.

Использует настройки из .env файла для подключения к Vespa.

Примеры использования:

# Синхронный поиск (только текст)
from utils.search_documents import search_documents
results = search_documents(["защитный слой", "бетон"], ["СП 63.13330.2018"])

# Поиск с изображениями
from utils.search_documents import search_documents_with_images
results = search_documents_with_images(["защитный слой", "бетон"], include_images=True)

# Асинхронный поиск с изображениями
import asyncio
from utils.search_documents import search_documents_with_images_async

async def main():
    results = await search_documents_with_images_async(["защитный слой"])
    print(results)

asyncio.run(main())

Переменные окружения (.env файл):
- VESPA_LOCAL_URL: URL сервера Vespa (обязательно)
- VESPA_LOCAL_PORT: Порт сервера Vespa (обязательно)
- IMG_CACHE_DIR: Директория для кэширования изображений (опционально)
"""

import json
import os
import asyncio
import logging
import base64
import io
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    raise ImportError("python-dotenv не установлен. Установите: pip install python-dotenv")

try:
    from vespa.application import Vespa
    VESPA_AVAILABLE = True
except ImportError:
    raise ImportError("pyvespa не установлен. Установите: pip install pyvespa")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL не установлен. Функции сжатия изображений недоступны. Установите: pip install Pillow")

# Настройка логирования
logger = logging.getLogger(__name__)



class DocumentSearchClient:
    """
    Клиент для поиска документов в нормативной базе через Vespa с поддержкой изображений.
    """
    
    def __init__(self):
        """Инициализация клиента поиска."""
        self.vespa_client = None
        self.img_cache_dir = None
        self._init_vespa()
        self._init_cache_dir()
        
    def _init_vespa(self):
        """Инициализация Vespa клиента"""
        print(f"🔍 DocumentSearchClient: инициализация Vespa")
        load_dotenv()
        
        vespa_url = os.environ.get("VESPA_LOCAL_URL")
        vespa_port = os.environ.get("VESPA_LOCAL_PORT")
        
        print(f"🔍 DocumentSearchClient: vespa_url = {vespa_url}")
        print(f"🔍 DocumentSearchClient: vespa_port = {vespa_port}")
        
        if not vespa_url:
            print(f"🔍 DocumentSearchClient: VESPA_LOCAL_URL не задан")
            logger.error("VESPA_LOCAL_URL не задан в .env файле")
            raise ValueError("VESPA_LOCAL_URL не задан в .env файле")
        if not vespa_port:
            print(f"🔍 DocumentSearchClient: VESPA_LOCAL_PORT не задан")
            logger.error("VESPA_LOCAL_PORT не задан в .env файле")
            raise ValueError("VESPA_LOCAL_PORT не задан в .env файле")
        
        try:
            print(f"🔍 DocumentSearchClient: подключаемся к Vespa {vespa_url}:{vespa_port}")
            self.vespa_client = Vespa(url=vespa_url, port=int(vespa_port))
            self.vespa_client.wait_for_application_up()
            print(f"✅ DocumentSearchClient: подключение к Vespa успешно")
            logger.info(f"Подключение к Vespa успешно: {vespa_url}:{vespa_port}")
        except Exception as e:
            print(f"❌ DocumentSearchClient: не удалось подключиться к Vespa: {e}")
            logger.error(f"Не удалось подключиться к Vespa {vespa_url}:{vespa_port}: {e}")
            raise

    def _init_cache_dir(self):
        """Инициализация директории для кэширования изображений"""
        cache_dir = os.environ.get("IMG_CACHE_DIR", "./img_cache")
        self.img_cache_dir = Path(cache_dir)
        self.img_cache_dir.mkdir(exist_ok=True)
        logger.info(f"Директория кэширования изображений: {self.img_cache_dir}")

    def _compress_image(self, img_path: Path, max_size=(1680, 1680), quality=80):
        """Сжимает изображение для экономии токенов."""
        if not PIL_AVAILABLE:
            logger.warning("PIL недоступен, сжатие изображений невозможно")
            return None
            
        try:
            with Image.open(img_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background
                
                # Изменяем размер если изображение слишком большое
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Сохраняем в буфер с пониженным качеством
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=quality, optimize=True)
                
                return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Ошибка сжатия изображения {img_path}: {e}")
            return None
    
    def _compress_base64_image(self, base64_data: str, max_size=(1680, 1680), quality=80):
        """Сжимает base64 изображение."""
        if not PIL_AVAILABLE:
            logger.warning("PIL недоступен, сжатие изображений невозможно")
            return base64_data
            
        try:
            # Декодируем base64
            img_data = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_data))
            
            # Конвертируем в RGB если нужно
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            
            # Изменяем размер если изображение слишком большое
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Сохраняем в буфер с пониженным качеством
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=quality, optimize=True)
            
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Ошибка сжатия base64 изображения: {e}")
            return base64_data  # Возвращаем оригинал если не удалось сжать

    async def _get_full_image_from_vespa(self, doc_id: str) -> Optional[str]:
        """Получает полное изображение из Vespa по ID документа."""
        if not self.vespa_client:
            logger.error("Vespa клиент не инициализирован")
            return None
            
        try:
            # Используем тот же подход, что и в рабочем коде - contains вместо точного равенства
            async with self.vespa_client.asyncio(connections=1) as session:
                response = await session.query(
                    body={
                        "yql": f'select full_image from pdf_page where id contains "{doc_id}"',
                        "ranking": "unranked",
                        "presentation.timing": True,
                        "ranking.matching.numThreadsPerSearch": 1,
                    }
                )
                
                if response.is_successful():
                    children = response.json.get("root", {}).get("children", [])
                    if children:
                        image_data = children[0]["fields"]["full_image"]
                        if image_data:
                            logger.debug(f"Получено изображение для {doc_id}, размер: {len(image_data)} символов")
                            return image_data
                        else:
                            logger.warning(f"Поле full_image пустое для {doc_id}")
                    else:
                        logger.warning(f"Документ с ID {doc_id} не найден")
                else:
                    logger.error(f"Ошибка запроса Vespa: {response.json}")
                    
        except Exception as e:
            logger.error(f"Ошибка получения изображения из Vespa для {doc_id}: {e}")
            
        return None

    async def search_documents_with_images_async(
        self, 
        semantic_keywords: List[str], 
        expected_documents: Optional[List[str]] = None,
        hits: int = 3,
        include_images: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Асинхронный поиск документов в Vespa с поддержкой изображений.
        
        Args:
            semantic_keywords: Ключевые слова для поиска
            expected_documents: Ожидаемые коды документов
            hits: Количество результатов
            include_images: Включать ли изображения в Vision API формате
            
        Returns:
            Список найденных документов с изображениями или None
        """
        # Сначала получаем обычные результаты поиска
        results = await self.search_documents_async(semantic_keywords, expected_documents, hits)
        
        if not results or not include_images:
            return results
        
        # Дополняем результаты изображениями
        enhanced_results = []
        images_data = {}
        
        for result in results:
            doc_id = result.get("image_id", "")
            
            if doc_id:
                # Проверяем кэш
                if self.img_cache_dir:
                    img_path = self.img_cache_dir / f"{doc_id}.jpg"
                else:
                    continue
                
                if img_path.exists():
                    try:
                        # Сжимаем изображение перед кодированием
                        img_data = self._compress_image(img_path)
                        if img_data:
                            images_data[doc_id] = img_data
                            logger.debug(f"Получено сжатое изображение для {doc_id} из кэша")
                    except Exception as e:
                        logger.error(f"Ошибка чтения кэшированного изображения для {doc_id}: {e}")
                
                # Получаем из Vespa если нет в кэше
                if doc_id not in images_data:
                    try:
                        img_data = await self._get_full_image_from_vespa(doc_id)
                        if img_data:
                            # Сжимаем изображение из Vespa
                            compressed_img = self._compress_base64_image(img_data)
                            if compressed_img:
                                images_data[doc_id] = compressed_img
                                # Кэшируем сжатое изображение
                                try:
                                    with open(img_path, "wb") as f:
                                        f.write(base64.b64decode(compressed_img))
                                    logger.debug(f"Кэшировано сжатое изображение для {doc_id}")
                                except Exception as e:
                                    logger.error(f"Не удалось кэшировать изображение для {doc_id}: {e}")
                    except Exception as e:
                        logger.error(f"Ошибка получения изображения из Vespa для {doc_id}: {e}")
            
            # Создаем улучшенный результат
            enhanced_result = result.copy()
            
            # Добавляем изображение в Vision API формате если есть
            if doc_id in images_data:
                enhanced_result["vision_content"] = [
                    {
                        "type": "image_url",
                        "min_pixels": 512 * 28 * 28,
                        "max_pixels": 1680 * 28 * 28,
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{images_data[doc_id]}",
                        },
                    }
                ]
                enhanced_result["has_image"] = True
            else:
                enhanced_result["has_image"] = False
            
            enhanced_results.append(enhanced_result)
        
        logger.info(f"Найдено {len(enhanced_results)} документов с {len(images_data)} изображениями")
        return enhanced_results

    async def search_documents_async(
        self, 
        semantic_keywords: List[str], 
        expected_documents: Optional[List[str]] = None,
        hits: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Асинхронный поиск документов в Vespa (только текст).
        
        Args:
            semantic_keywords: Ключевые слова для поиска
            expected_documents: Ожидаемые коды документов (например, ["СП 63.13330.2018"])
            hits: Количество результатов
            
        Returns:
            Список найденных документов или None
        """
        # Проверяем что Vespa клиент инициализирован
        if not self.vespa_client:
            logger.error("Vespa клиент не инициализирован")
            return None
        
        # Реальный поиск через Vespa
        try:
            query = " ".join(semantic_keywords)
            
            # Формирование фильтра по кодам документов
            filter_clause = ""
            if expected_documents:
                # Создаем OR условия для каждого документа
                doc_conditions = []
                for doc in expected_documents:
                    # Используем contains для частичного соответствия и matches для точного
                    if "СП 63" in doc:
                        # Специальная обработка для СП 63 - ищем разные варианты
                        doc_conditions.append('(doc_code contains "СП 63" or doc_code contains "СП63")')
                    else:
                        # Для других документов используем contains для частичного поиска
                        doc_conditions.append(f'doc_code contains "{doc}"')
                
                if doc_conditions:
                    filter_clause = f' and ({" or ".join(doc_conditions)})'
                    print(f"🔍 Применяется фильтр по документам: {expected_documents}")
            else:
                print(f"🔍 Поиск БЕЗ фильтра по документам")
            
            yql = f"select id,title,doc_code,page_number,snippet,text from pdf_page where userQuery(){filter_clause}"
            
            print(f"🔍 Vespa запрос:")
            print(f"   query = '{query}'")
            print(f"   filter_clause = '{filter_clause}'")
            print(f"   yql = '{yql}'")
            print(f"   hits = {hits}")
            
            async with self.vespa_client.asyncio(connections=1) as session:
                request_body = {
                    "yql": yql,
                    "ranking": "bm25",
                    "query": query,
                    "timeout": "10s",
                    "hits": hits,
                    "presentation.timing": True,
                }
                print(f"🔍 Vespa request body: {request_body}")
                
                response = await session.query(body=request_body)
                
                print(f"🔍 Vespa response:")
                print(f"   is_successful = {response.is_successful()}")
                print(f"   status_code = {getattr(response, 'status_code', 'unknown')}")
                
                if response.is_successful():
                    hits_data = response.json.get("root", {}).get("children", [])
                    print(f"🔍 Vespa hits: {len(hits_data)}")
                    
                    if not hits_data:
                        logger.warning("Vespa вернул пустой результат")
                        return None
                    
                    results = []
                    for hit in hits_data:
                        fields = hit.get("fields", {})
                        
                        # Отладка полей документа
                        print(f"🔍 Документ {fields.get('id', 'unknown')}:")
                        print(f"   title = {fields.get('title', 'N/A')}")
                        print(f"   doc_code = {fields.get('doc_code', 'N/A')}")
                        print(f"   page_number = {fields.get('page_number', 'N/A')}")
                        
                        result = {
                            "image_id": fields.get("id", ""),
                            "source_document": fields.get("doc_code", "Неизвестный документ"),
                            "page_number": fields.get("page_number", 0),
                            "content_preview": fields.get("snippet", fields.get("text", ""))[:300] + "..." if fields.get("snippet") or fields.get("text") else "Содержимое недоступно",
                            "title": fields.get("title", ""),
                            "full_text": fields.get("text", "")
                        }
                        results.append(result)
                    
                    logger.info(f"Vespa поиск: найдено {len(results)} документов")
                    return results
                else:
                    logger.error(f"Vespa запрос неуспешен: {response.json}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка поиска в Vespa: {e}", exc_info=True)
            return None

# Глобальный экземпляр клиента
_global_client = None

def get_client():
    """Получить глобальный экземпляр клиента."""
    global _global_client
    if _global_client is None:
        _global_client = DocumentSearchClient()
    return _global_client

def search_documents(
    semantic_keywords: List[str], 
    expected_documents: Optional[List[str]] = None,
    hits: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """
    Синхронный поиск документов (обертка для асинхронной функции).
    
    Args:
        semantic_keywords: Ключевые слова для поиска
        expected_documents: Ожидаемые коды документов
        hits: Количество результатов
        
    Returns:
        Список найденных документов или None
    """
    client = get_client()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        client.search_documents_async(semantic_keywords, expected_documents, hits)
    )

def search_documents_with_images(
    semantic_keywords: List[str], 
    expected_documents: Optional[List[str]] = None,
    hits: int = 3,
    include_images: bool = True
) -> Optional[List[Dict[str, Any]]]:
    """
    Синхронный поиск документов с изображениями.
    
    Args:
        semantic_keywords: Ключевые слова для поиска
        expected_documents: Ожидаемые коды документов
        hits: Количество результатов
        include_images: Включать ли изображения в Vision API формате
        
    Returns:
        Список найденных документов с изображениями или None
    """
    client = get_client()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        client.search_documents_with_images_async(semantic_keywords, expected_documents, hits, include_images)
    )

async def search_documents_async(
    semantic_keywords: List[str], 
    expected_documents: Optional[List[str]] = None,
    hits: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """
    Асинхронный поиск документов (обертка).
    
    Args:
        semantic_keywords: Ключевые слова для поиска
        expected_documents: Ожидаемые коды документов
        hits: Количество результатов
        
    Returns:
        Список найденных документов или None
    """
    client = get_client()
    return await client.search_documents_async(semantic_keywords, expected_documents, hits)

async def search_documents_with_images_async(
    semantic_keywords: List[str], 
    expected_documents: Optional[List[str]] = None,
    hits: int = 3,
    include_images: bool = True
) -> Optional[List[Dict[str, Any]]]:
    """
    Асинхронный поиск документов с изображениями (обертка).
    
    Args:
        semantic_keywords: Ключевые слова для поиска
        expected_documents: Ожидаемые коды документов
        hits: Количество результатов
        include_images: Включать ли изображения в Vision API формате
        
    Returns:
        Список найденных документов с изображениями или None
    """
    client = get_client()
    return await client.search_documents_with_images_async(semantic_keywords, expected_documents, hits, include_images)

if __name__ == "__main__":
    # Тест синхронного поиска
    print("=== Тест синхронного поиска ===")
    try:
        results = search_documents(["защитный слой", "бетон"])
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['source_document']} (стр. {result['page_number']})")
        else:
            print("Результаты не найдены")
    except Exception as e:
        print(f"Ошибка поиска: {e}")
    
    # Тест поиска с изображениями
    print("\n=== Тест поиска с изображениями ===")
    try:
        results_with_images = search_documents_with_images(["защитный слой"], include_images=True)
        if results_with_images:
            for i, result in enumerate(results_with_images, 1):
                print(f"{i}. {result['source_document']}")
                print(f"   Изображение: {'✅' if result.get('has_image') else '❌'}")
                if result.get('vision_content'):
                    print(f"   Vision API формат: готов")
        else:
            print("Результаты не найдены")
    except Exception as e:
        print(f"Ошибка поиска с изображениями: {e}")
    
    # Тест асинхронного поиска
    async def test_async():
        print("\n=== Тест асинхронного поиска с изображениями ===")
        try:
            results = await search_documents_with_images_async(["арматура"], include_images=True)
            if results:
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result['source_document']}")
                    print(f"   Изображение: {'✅' if result.get('has_image') else '❌'}")
            else:
                print("Результаты не найдены")
        except Exception as e:
            print(f"Ошибка асинхронного поиска: {e}")
    
    asyncio.run(test_async()) 