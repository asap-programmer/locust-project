"""
Конфигурация для нагрузочного тестирования.

Централизованные настройки для тестов REST и gRPC.

Автор: VKR Project
"""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ServerConfig:
    """Конфигурация серверов."""
    rest_host: str = "http://localhost:8000"
    grpc_host: str = "localhost:50051"


@dataclass
class TestScenario:
    """Конфигурация тестового сценария."""
    name: str
    description: str
    users: int
    spawn_rate: int
    run_time: str
    max_response_time_ms: int = 1000
    max_error_rate: float = 0.05


# Предопределённые тестовые сценарии
SCENARIOS = {
    "sanity": TestScenario(
        name="Лёгкая нагрузка (Sanity Check)",
        description="Проверка базовой работоспособности системы",
        users=5,
        spawn_rate=1,
        run_time="1m",
        max_response_time_ms=500,
        max_error_rate=0.01
    ),
    "normal": TestScenario(
        name="Рабочая нагрузка (Normal)",
        description="Имитация реалистичного использования",
        users=20,
        spawn_rate=2,
        run_time="3m",
        max_response_time_ms=1000,
        max_error_rate=0.05
    ),
    "stress": TestScenario(
        name="Стресс-тест (Stress)",
        description="Выявление пределов производительности",
        users=100,
        spawn_rate=10,
        run_time="5m",
        max_response_time_ms=3000,
        max_error_rate=0.1
    ),
    "stability": TestScenario(
        name="Тест на стабильность (Stability)",
        description="Проверка деградации при длительной нагрузке",
        users=30,
        spawn_rate=3,
        run_time="10m",
        max_response_time_ms=1500,
        max_error_rate=0.05
    ),
    "peak": TestScenario(
        name="Пиковая нагрузка (Peak)",
        description="Определение максимальной пропускной способности",
        users=200,
        spawn_rate=20,
        run_time="3m",
        max_response_time_ms=5000,
        max_error_rate=0.2
    ),
    "ramp_up": TestScenario(
        name="Постепенное увеличение (Ramp Up)",
        description="Плавное увеличение нагрузки для наблюдения за поведением",
        users=50,
        spawn_rate=1,
        run_time="5m",
        max_response_time_ms=2000,
        max_error_rate=0.1
    )
}


# Данные для тестирования
EXISTING_KEYWORDS = [
    "Blockchain",
    "Consensus",
    "Smart Contract",
    "Ethereum",
    "Hyperledger Fabric",
    "TPS",
    "Latency",
    "Gas",
    "Proof of Work",
    "Proof of Stake",
    "Sharding",
    "Throughput"
]

CATEGORIES = [
    "Основные понятия",
    "Механизмы консенсуса",
    "Технологии",
    "Платформы",
    "Метрики производительности",
    "Экономика блокчейна",
    "Масштабирование"
]


# Веса задач (определяют частоту выполнения)
TASK_WEIGHTS = {
    # Операции чтения (высокий приоритет)
    "get_all_terms": 10,
    "get_term_by_keyword": 8,
    "get_terms_with_pagination": 5,
    "get_terms_by_category": 4,
    "get_categories": 3,
    "health_check": 2,

    # Операции записи (низкий приоритет)
    "create_term": 2,
    "update_term": 1,
    "delete_term": 1
}


# Профили пользователей
USER_PROFILES = {
    "reader": {
        "description": "Пользователь, преимущественно читающий данные",
        "read_weight": 90,
        "write_weight": 10
    },
    "writer": {
        "description": "Пользователь, активно создающий/изменяющий данные",
        "read_weight": 30,
        "write_weight": 70
    },
    "balanced": {
        "description": "Пользователь с балансом чтения и записи",
        "read_weight": 60,
        "write_weight": 40
    }
}


def get_env_or_default(key: str, default: str) -> str:
    """Получение значения из окружения или значения по умолчанию."""
    return os.environ.get(key, default)


# Инициализация конфигурации из переменных окружения
SERVER_CONFIG = ServerConfig(
    rest_host=get_env_or_default("REST_HOST", "http://localhost:8000"),
    grpc_host=get_env_or_default("GRPC_HOST", "localhost:50051")
)
