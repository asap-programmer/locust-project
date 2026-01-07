"""
Locust тесты для REST API глоссария блокчейн-терминов.

Этот файл содержит тестовые сценарии для нагрузочного тестирования
FastAPI REST-приложения с использованием Locust.

Запуск:
    locust -f locustfile_rest.py --host=http://localhost:8000

Автор: VKR Project
"""

import random
import string
from locust import HttpUser, task, between, constant, events
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Предопределённые ключевые слова для поиска (из базы данных)
EXISTING_KEYWORDS = [
    "Blockchain", "Consensus", "Smart Contract", "Ethereum",
    "Hyperledger Fabric", "TPS", "Latency", "Gas",
    "Proof of Work", "Proof of Stake", "Sharding", "Throughput"
]

# Категории для фильтрации
CATEGORIES = [
    "Основные понятия", "Механизмы консенсуса", "Технологии",
    "Платформы", "Метрики производительности", "Экономика блокчейна",
    "Масштабирование"
]


def generate_random_string(length=10):
    """Генерация случайной строки для уникальных терминов."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_term_data():
    """Генерация данных для нового термина."""
    return {
        "keyword": f"TestTerm_{generate_random_string(8)}",
        "definition": f"Это тестовое определение термина для нагрузочного тестирования. "
                      f"Содержит достаточно символов для валидации. ID: {generate_random_string(16)}",
        "category": random.choice(CATEGORIES)
    }


class GlossaryRESTUser(HttpUser):
    """
    Класс пользователя для тестирования REST API глоссария.

    Моделирует реалистичное поведение пользователя:
    - Чаще выполняет операции чтения (GET)
    - Реже выполняет операции записи (POST, PUT, DELETE)
    - Включает паузы между запросами
    """

    # Время ожидания между запросами (от 1 до 3 секунд)
    wait_time = between(1, 3)

    # Для хранения созданных терминов (для последующего удаления)
    created_terms = []

    def on_start(self):
        """Выполняется при старте каждого пользователя."""
        logger.info(f"Пользователь начал сессию")
        # Проверка доступности сервиса
        response = self.client.get("/health")
        if response.status_code != 200:
            logger.error("Сервис недоступен!")

    def on_stop(self):
        """Выполняется при завершении сессии пользователя."""
        logger.info(f"Пользователь завершил сессию. Создано терминов: {len(self.created_terms)}")

    # ===== ОПЕРАЦИИ ЧТЕНИЯ (высокий приоритет) =====

    @task(10)
    def get_all_terms(self):
        """
        Получение списка всех терминов.
        Вес: 10 - наиболее частая операция.
        """
        with self.client.get(
            "/terms",
            name="GET /terms - Получить все термины",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(8)
    def get_term_by_keyword(self):
        """
        Получение термина по ключевому слову.
        Вес: 8 - частая операция поиска.
        """
        keyword = random.choice(EXISTING_KEYWORDS)
        with self.client.get(
            f"/terms/{keyword}",
            name="GET /terms/{keyword} - Получить термин",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Термин не найден - допустимо
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(5)
    def get_terms_with_pagination(self):
        """
        Получение терминов с пагинацией.
        Вес: 5 - умеренно частая операция.
        """
        skip = random.randint(0, 5)
        limit = random.randint(5, 20)
        with self.client.get(
            f"/terms?skip={skip}&limit={limit}",
            name="GET /terms?pagination - Пагинация",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(4)
    def get_terms_by_category(self):
        """
        Фильтрация терминов по категории.
        Вес: 4 - умеренная операция.
        """
        category = random.choice(CATEGORIES)
        with self.client.get(
            f"/terms?category={category}",
            name="GET /terms?category - Фильтр по категории",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(3)
    def get_categories(self):
        """
        Получение списка категорий.
        Вес: 3 - редкая операция.
        """
        with self.client.get(
            "/categories",
            name="GET /categories - Список категорий",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def health_check(self):
        """
        Проверка здоровья сервиса.
        Вес: 2 - редкая служебная операция.
        """
        with self.client.get(
            "/health",
            name="GET /health - Проверка здоровья",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    # ===== ОПЕРАЦИИ ЗАПИСИ (низкий приоритет) =====

    @task(2)
    def create_term(self):
        """
        Создание нового термина.
        Вес: 2 - редкая операция записи.
        """
        term_data = generate_term_data()
        with self.client.post(
            "/terms",
            json=term_data,
            name="POST /terms - Создать термин",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                self.created_terms.append(term_data["keyword"])
                response.success()
            elif response.status_code == 400:
                response.success()  # Термин уже существует - допустимо
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def update_term(self):
        """
        Обновление существующего термина.
        Вес: 1 - редкая операция.
        """
        keyword = random.choice(EXISTING_KEYWORDS)
        update_data = {
            "definition": f"Обновлённое определение для тестирования. Timestamp: {time.time()}"
        }
        with self.client.put(
            f"/terms/{keyword}",
            json=update_data,
            name="PUT /terms/{keyword} - Обновить термин",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Термин не найден - допустимо
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def delete_created_term(self):
        """
        Удаление созданного термина.
        Вес: 1 - редкая операция.
        """
        if self.created_terms:
            keyword = self.created_terms.pop()
            with self.client.delete(
                f"/terms/{keyword}",
                name="DELETE /terms/{keyword} - Удалить термин",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 404:
                    response.success()  # Уже удалён - допустимо
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")


class GlossaryRESTReadOnlyUser(HttpUser):
    """
    Пользователь только для операций чтения.
    Используется для тестирования производительности read-heavy нагрузки.
    """

    wait_time = between(0.5, 1.5)

    @task(5)
    def get_all_terms(self):
        """Получение всех терминов."""
        self.client.get("/terms", name="[ReadOnly] GET /terms")

    @task(5)
    def get_term_by_keyword(self):
        """Получение термина по ключевому слову."""
        keyword = random.choice(EXISTING_KEYWORDS)
        self.client.get(f"/terms/{keyword}", name="[ReadOnly] GET /terms/{keyword}")

    @task(2)
    def get_categories(self):
        """Получение категорий."""
        self.client.get("/categories", name="[ReadOnly] GET /categories")


class GlossaryRESTWriteHeavyUser(HttpUser):
    """
    Пользователь с преобладанием операций записи.
    Используется для стресс-тестирования операций создания/обновления.
    """

    wait_time = between(0.3, 1)
    created_terms = []

    @task(3)
    def create_term(self):
        """Создание термина."""
        term_data = generate_term_data()
        response = self.client.post(
            "/terms",
            json=term_data,
            name="[WriteHeavy] POST /terms"
        )
        if response.status_code == 201:
            self.created_terms.append(term_data["keyword"])

    @task(2)
    def update_existing_term(self):
        """Обновление существующего термина."""
        keyword = random.choice(EXISTING_KEYWORDS)
        self.client.put(
            f"/terms/{keyword}",
            json={"definition": f"Updated at {time.time()}"},
            name="[WriteHeavy] PUT /terms/{keyword}"
        )

    @task(1)
    def get_all_terms(self):
        """Чтение для проверки."""
        self.client.get("/terms", name="[WriteHeavy] GET /terms")

    @task(1)
    def cleanup_created_terms(self):
        """Очистка созданных терминов."""
        if self.created_terms:
            keyword = self.created_terms.pop()
            self.client.delete(
                f"/terms/{keyword}",
                name="[WriteHeavy] DELETE /terms/{keyword}"
            )


# ===== Обработчики событий Locust =====

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Обработчик начала теста."""
    logger.info("=" * 60)
    logger.info("НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ REST API")
    logger.info(f"Хост: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Обработчик завершения теста."""
    logger.info("=" * 60)
    logger.info("ЗАВЕРШЕНИЕ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ REST API")

    # Вывод статистики
    stats = environment.stats
    logger.info(f"Всего запросов: {stats.total.num_requests}")
    logger.info(f"Ошибок: {stats.total.num_failures}")
    logger.info(f"Средний RPS: {stats.total.current_rps:.2f}")
    logger.info(f"Среднее время ответа: {stats.total.avg_response_time:.2f} ms")

    if stats.total.num_requests > 0:
        error_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        logger.info(f"Процент ошибок: {error_rate:.2f}%")

    logger.info("=" * 60)


if __name__ == "__main__":
    import os
    os.system("locust -f locustfile_rest.py --host=http://localhost:8000")
