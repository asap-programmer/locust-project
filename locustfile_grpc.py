"""
Locust тесты для gRPC сервиса глоссария блокчейн-терминов.

Этот файл содержит тестовые сценарии для нагрузочного тестирования
gRPC-приложения с использованием Locust и locust-plugins.

Запуск:
    locust -f locustfile_grpc.py --host=localhost:50051

Автор: VKR Project
"""

import random
import string
import time
import logging
import grpc
from locust import User, task, between, events
from locust.exception import LocustError

# Импорт сгенерированных proto классов
try:
    import glossary_pb2
    import glossary_pb2_grpc
except ImportError:
    raise ImportError(
        "Не найдены сгенерированные proto файлы. "
        "Запустите: python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/glossary.proto"
    )

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Предопределённые ключевые слова для поиска
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
    """Генерация случайной строки."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_term_data():
    """Генерация данных для нового термина."""
    return {
        "keyword": f"TestTerm_{generate_random_string(8)}",
        "definition": f"Это тестовое определение термина для нагрузочного тестирования gRPC. "
                      f"Содержит достаточно символов. ID: {generate_random_string(16)}",
        "category": random.choice(CATEGORIES)
    }


class GrpcClient:
    """
    Обёртка над gRPC клиентом для интеграции с Locust.
    Реализует измерение времени выполнения запросов.
    """

    def __init__(self, host: str, user: User):
        self.host = host
        self.user = user
        self.channel = None
        self.stub = None
        self._connect()

    def _connect(self):
        """Установка gRPC соединения."""
        try:
            self.channel = grpc.insecure_channel(self.host)
            self.stub = glossary_pb2_grpc.GlossaryServiceStub(self.channel)
            logger.debug(f"Connected to gRPC server at {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def close(self):
        """Закрытие соединения."""
        if self.channel:
            self.channel.close()

    def _fire_success(self, request_type: str, name: str, response_time: float, response_length: int = 0):
        """Отправка события успешного запроса в Locust."""
        self.user.environment.events.request.fire(
            request_type=request_type,
            name=name,
            response_time=response_time,
            response_length=response_length,
            exception=None,
            context={}
        )

    def _fire_failure(self, request_type: str, name: str, response_time: float, exception: Exception):
        """Отправка события неудачного запроса в Locust."""
        self.user.environment.events.request.fire(
            request_type=request_type,
            name=name,
            response_time=response_time,
            response_length=0,
            exception=exception,
            context={}
        )

    def health_check(self):
        """Проверка здоровья сервиса."""
        name = "gRPC HealthCheck"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.HealthCheckRequest()
            response = self.stub.HealthCheck(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_failure("gRPC", name, response_time, e)
            raise

    def get_all_terms(self, skip: int = 0, limit: int = 100, category: str = ""):
        """Получение всех терминов."""
        name = "gRPC GetAllTerms"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.GetAllTermsRequest(
                skip=skip,
                limit=limit,
                category=category
            )
            response = self.stub.GetAllTerms(request)
            response_time = (time.perf_counter() - start_time) * 1000
            response_length = len(response.terms)
            self._fire_success("gRPC", name, response_time, response_length)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_failure("gRPC", name, response_time, e)
            raise

    def get_term(self, keyword: str):
        """Получение термина по ключевому слову."""
        name = "gRPC GetTerm"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.GetTermRequest(keyword=keyword)
            response = self.stub.GetTerm(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time, 1)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            # NOT_FOUND не считаем ошибкой
            if e.code() == grpc.StatusCode.NOT_FOUND:
                self._fire_success("gRPC", name, response_time, 0)
            else:
                self._fire_failure("gRPC", name, response_time, e)
            raise

    def create_term(self, keyword: str, definition: str, category: str = ""):
        """Создание нового термина."""
        name = "gRPC CreateTerm"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.CreateTermRequest(
                keyword=keyword,
                definition=definition,
                category=category
            )
            response = self.stub.CreateTerm(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time, 1)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            # ALREADY_EXISTS не считаем ошибкой
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                self._fire_success("gRPC", name, response_time, 0)
            else:
                self._fire_failure("gRPC", name, response_time, e)
            raise

    def update_term(self, keyword: str, definition: str = "", category: str = ""):
        """Обновление термина."""
        name = "gRPC UpdateTerm"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.UpdateTermRequest(
                keyword=keyword,
                definition=definition,
                category=category
            )
            response = self.stub.UpdateTerm(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time, 1)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            if e.code() == grpc.StatusCode.NOT_FOUND:
                self._fire_success("gRPC", name, response_time, 0)
            else:
                self._fire_failure("gRPC", name, response_time, e)
            raise

    def delete_term(self, keyword: str):
        """Удаление термина."""
        name = "gRPC DeleteTerm"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.DeleteTermRequest(keyword=keyword)
            response = self.stub.DeleteTerm(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time, 1)
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            if e.code() == grpc.StatusCode.NOT_FOUND:
                self._fire_success("gRPC", name, response_time, 0)
            else:
                self._fire_failure("gRPC", name, response_time, e)
            raise

    def get_categories(self):
        """Получение списка категорий."""
        name = "gRPC GetCategories"
        start_time = time.perf_counter()
        try:
            request = glossary_pb2.GetCategoriesRequest()
            response = self.stub.GetCategories(request)
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_success("gRPC", name, response_time, len(response.categories))
            return response
        except grpc.RpcError as e:
            response_time = (time.perf_counter() - start_time) * 1000
            self._fire_failure("gRPC", name, response_time, e)
            raise


class GlossaryGrpcUser(User):
    """
    Класс пользователя для тестирования gRPC сервиса глоссария.

    Моделирует реалистичное поведение пользователя:
    - Чаще выполняет операции чтения
    - Реже выполняет операции записи
    """

    # Время ожидания между запросами
    wait_time = between(1, 3)

    # Для хранения созданных терминов
    created_terms = []

    def on_start(self):
        """Выполняется при старте пользователя."""
        # Получение хоста из настроек Locust
        host = self.host if self.host else "localhost:50051"
        # Убираем возможные префиксы http/https
        host = host.replace("http://", "").replace("https://", "")
        self.grpc_client = GrpcClient(host, self)
        logger.info(f"gRPC пользователь подключен к {host}")

        # Проверка доступности сервиса
        try:
            self.grpc_client.health_check()
        except Exception as e:
            logger.error(f"Сервис недоступен: {e}")

    def on_stop(self):
        """Выполняется при завершении пользователя."""
        if hasattr(self, 'grpc_client'):
            self.grpc_client.close()
        logger.info(f"gRPC пользователь отключен. Создано терминов: {len(self.created_terms)}")

    # ===== ОПЕРАЦИИ ЧТЕНИЯ =====

    @task(10)
    def get_all_terms(self):
        """Получение всех терминов."""
        try:
            self.grpc_client.get_all_terms()
        except grpc.RpcError:
            pass

    @task(8)
    def get_term_by_keyword(self):
        """Получение термина по ключевому слову."""
        keyword = random.choice(EXISTING_KEYWORDS)
        try:
            self.grpc_client.get_term(keyword)
        except grpc.RpcError:
            pass

    @task(5)
    def get_terms_with_pagination(self):
        """Получение терминов с пагинацией."""
        skip = random.randint(0, 5)
        limit = random.randint(5, 20)
        try:
            self.grpc_client.get_all_terms(skip=skip, limit=limit)
        except grpc.RpcError:
            pass

    @task(4)
    def get_terms_by_category(self):
        """Фильтрация по категории."""
        category = random.choice(CATEGORIES)
        try:
            self.grpc_client.get_all_terms(category=category)
        except grpc.RpcError:
            pass

    @task(3)
    def get_categories(self):
        """Получение списка категорий."""
        try:
            self.grpc_client.get_categories()
        except grpc.RpcError:
            pass

    @task(2)
    def health_check(self):
        """Проверка здоровья."""
        try:
            self.grpc_client.health_check()
        except grpc.RpcError:
            pass

    # ===== ОПЕРАЦИИ ЗАПИСИ =====

    @task(2)
    def create_term(self):
        """Создание нового термина."""
        term_data = generate_term_data()
        try:
            self.grpc_client.create_term(
                keyword=term_data["keyword"],
                definition=term_data["definition"],
                category=term_data["category"]
            )
            self.created_terms.append(term_data["keyword"])
        except grpc.RpcError:
            pass

    @task(1)
    def update_term(self):
        """Обновление существующего термина."""
        keyword = random.choice(EXISTING_KEYWORDS)
        try:
            self.grpc_client.update_term(
                keyword=keyword,
                definition=f"Обновлённое определение gRPC. Timestamp: {time.time()}"
            )
        except grpc.RpcError:
            pass

    @task(1)
    def delete_created_term(self):
        """Удаление созданного термина."""
        if self.created_terms:
            keyword = self.created_terms.pop()
            try:
                self.grpc_client.delete_term(keyword)
            except grpc.RpcError:
                pass


class GlossaryGrpcReadOnlyUser(User):
    """
    Пользователь только для операций чтения gRPC.
    """

    wait_time = between(0.5, 1.5)

    def on_start(self):
        host = self.host if self.host else "localhost:50051"
        host = host.replace("http://", "").replace("https://", "")
        self.grpc_client = GrpcClient(host, self)

    def on_stop(self):
        if hasattr(self, 'grpc_client'):
            self.grpc_client.close()

    @task(5)
    def get_all_terms(self):
        try:
            self.grpc_client.get_all_terms()
        except grpc.RpcError:
            pass

    @task(5)
    def get_term_by_keyword(self):
        keyword = random.choice(EXISTING_KEYWORDS)
        try:
            self.grpc_client.get_term(keyword)
        except grpc.RpcError:
            pass

    @task(2)
    def get_categories(self):
        try:
            self.grpc_client.get_categories()
        except grpc.RpcError:
            pass


class GlossaryGrpcWriteHeavyUser(User):
    """
    Пользователь с преобладанием записи для gRPC.
    """

    wait_time = between(0.3, 1)
    created_terms = []

    def on_start(self):
        host = self.host if self.host else "localhost:50051"
        host = host.replace("http://", "").replace("https://", "")
        self.grpc_client = GrpcClient(host, self)

    def on_stop(self):
        if hasattr(self, 'grpc_client'):
            self.grpc_client.close()

    @task(3)
    def create_term(self):
        term_data = generate_term_data()
        try:
            self.grpc_client.create_term(
                keyword=term_data["keyword"],
                definition=term_data["definition"],
                category=term_data["category"]
            )
            self.created_terms.append(term_data["keyword"])
        except grpc.RpcError:
            pass

    @task(2)
    def update_existing_term(self):
        keyword = random.choice(EXISTING_KEYWORDS)
        try:
            self.grpc_client.update_term(
                keyword=keyword,
                definition=f"Updated gRPC at {time.time()}"
            )
        except grpc.RpcError:
            pass

    @task(1)
    def get_all_terms(self):
        try:
            self.grpc_client.get_all_terms()
        except grpc.RpcError:
            pass

    @task(1)
    def cleanup_created_terms(self):
        if self.created_terms:
            keyword = self.created_terms.pop()
            try:
                self.grpc_client.delete_term(keyword)
            except grpc.RpcError:
                pass


# ===== Обработчики событий Locust =====

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Обработчик начала теста."""
    logger.info("=" * 60)
    logger.info("НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ gRPC")
    logger.info(f"Хост: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Обработчик завершения теста."""
    logger.info("=" * 60)
    logger.info("ЗАВЕРШЕНИЕ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ gRPC")

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
    os.system("locust -f locustfile_grpc.py --host=localhost:50051")
