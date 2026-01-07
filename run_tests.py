#!/usr/bin/env python3
"""
Скрипт для автоматизированного запуска нагрузочных тестов.

Поддерживает различные сценарии тестирования:
- Лёгкая нагрузка (sanity check)
- Рабочая нагрузка (normal)
- Стресс-тест (stress)
- Тест на стабильность (stability)

Использование:
    python run_tests.py --scenario sanity --target rest
    python run_tests.py --scenario stress --target grpc
    python run_tests.py --scenario all --target both

Автор: VKR Project
"""

import argparse
import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path


# Конфигурация тестовых сценариев
SCENARIOS = {
    "sanity": {
        "name": "Лёгкая нагрузка (Sanity Check)",
        "description": "Проверка базовой работоспособности",
        "users": 5,
        "spawn_rate": 1,
        "run_time": "1m",
        "expected": {
            "max_response_time_ms": 500,
            "max_error_rate": 0.01
        }
    },
    "normal": {
        "name": "Рабочая нагрузка (Normal)",
        "description": "Имитация реалистичного использования",
        "users": 20,
        "spawn_rate": 2,
        "run_time": "3m",
        "expected": {
            "max_response_time_ms": 1000,
            "max_error_rate": 0.05
        }
    },
    "stress": {
        "name": "Стресс-тест (Stress)",
        "description": "Выявление пределов производительности",
        "users": 100,
        "spawn_rate": 10,
        "run_time": "5m",
        "expected": {
            "max_response_time_ms": 3000,
            "max_error_rate": 0.1
        }
    },
    "stability": {
        "name": "Тест на стабильность (Stability)",
        "description": "Проверка деградации при длительной нагрузке",
        "users": 30,
        "spawn_rate": 3,
        "run_time": "10m",
        "expected": {
            "max_response_time_ms": 1500,
            "max_error_rate": 0.05
        }
    },
    "peak": {
        "name": "Пиковая нагрузка (Peak)",
        "description": "Максимальная нагрузка для определения потолка",
        "users": 200,
        "spawn_rate": 20,
        "run_time": "3m",
        "expected": {
            "max_response_time_ms": 5000,
            "max_error_rate": 0.2
        }
    }
}

# Конфигурация целей тестирования
TARGETS = {
    "rest": {
        "locustfile": "locustfile_rest.py",
        "host": "http://localhost:8000",
        "name": "REST API"
    },
    "grpc": {
        "locustfile": "locustfile_grpc.py",
        "host": "localhost:50051",
        "name": "gRPC Service"
    }
}


def create_results_dir():
    """Создание директории для результатов."""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # Создаём поддиректорию с текущей датой/временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = results_dir / timestamp
    run_dir.mkdir(exist_ok=True)

    return run_dir


def run_locust_test(scenario_name: str, target_name: str, results_dir: Path, headless: bool = True):
    """
    Запуск Locust теста.

    Args:
        scenario_name: Название сценария (sanity, normal, stress, stability)
        target_name: Цель (rest, grpc)
        results_dir: Директория для результатов
        headless: Запуск без веб-интерфейса

    Returns:
        dict: Результаты теста
    """
    scenario = SCENARIOS[scenario_name]
    target = TARGETS[target_name]

    print("\n" + "=" * 70)
    print(f"ТЕСТ: {scenario['name']}")
    print(f"ЦЕЛЬ: {target['name']}")
    print(f"Описание: {scenario['description']}")
    print(f"Параметры: {scenario['users']} пользователей, "
          f"spawn rate: {scenario['spawn_rate']}/s, "
          f"длительность: {scenario['run_time']}")
    print("=" * 70)

    # Имена файлов для результатов
    result_prefix = f"{target_name}_{scenario_name}"
    csv_prefix = results_dir / result_prefix
    html_report = results_dir / f"{result_prefix}_report.html"
    json_report = results_dir / f"{result_prefix}_stats.json"

    # Формирование команды Locust
    cmd = [
        sys.executable, "-m", "locust",
        "-f", target["locustfile"],
        "--host", target["host"],
        "-u", str(scenario["users"]),
        "-r", str(scenario["spawn_rate"]),
        "-t", scenario["run_time"],
        "--csv", str(csv_prefix),
        "--html", str(html_report),
    ]

    if headless:
        cmd.append("--headless")

    print(f"\nЗапуск команды: {' '.join(cmd)}")
    print("\nВыполнение теста...")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        duration = time.time() - start_time

        # Парсинг результатов из CSV
        stats_csv = f"{csv_prefix}_stats.csv"
        test_results = parse_csv_results(stats_csv) if os.path.exists(stats_csv) else {}

        # Добавление метаданных
        test_results["scenario"] = scenario_name
        test_results["target"] = target_name
        test_results["duration_seconds"] = duration
        test_results["timestamp"] = datetime.now().isoformat()
        test_results["config"] = scenario

        # Сохранение JSON отчёта
        with open(json_report, "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        # Вывод результатов
        print("\n" + "-" * 50)
        print("РЕЗУЛЬТАТЫ:")
        print("-" * 50)

        if "total_requests" in test_results:
            print(f"  Всего запросов: {test_results.get('total_requests', 'N/A')}")
            print(f"  Ошибок: {test_results.get('failures', 'N/A')}")
            print(f"  RPS: {test_results.get('rps', 'N/A'):.2f}")
            print(f"  Среднее время ответа: {test_results.get('avg_response_time', 'N/A'):.2f} ms")
            print(f"  p95: {test_results.get('p95', 'N/A')} ms")
            print(f"  p99: {test_results.get('p99', 'N/A')} ms")

        print(f"\n  Отчёты сохранены в: {results_dir}")
        print(f"    - HTML: {html_report.name}")
        print(f"    - CSV: {result_prefix}_stats.csv")
        print(f"    - JSON: {json_report.name}")

        return test_results

    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения теста: {e}")
        print(f"STDERR: {e.stderr}")
        return {"error": str(e)}

    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
        return {"error": str(e)}


def parse_csv_results(csv_path: str) -> dict:
    """Парсинг CSV результатов Locust."""
    results = {}

    # Пробуем разные кодировки
    encodings = ["utf-8", "cp1251", "latin-1", "utf-8-sig"]
    lines = None

    for encoding in encodings:
        try:
            with open(csv_path, "r", encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None or len(lines) < 2:
        return results

    try:
        # Заголовки
        headers = lines[0].strip().split(",")

        # Ищем строку с Aggregated данными
        for line in lines[1:]:
            values = line.strip().split(",")
            if len(values) >= len(headers) and values[1] == "Aggregated":
                # Парсим значения
                for i, header in enumerate(headers):
                    header = header.strip('"')
                    value = values[i].strip('"') if i < len(values) else ""

                    if header == "Request Count":
                        results["total_requests"] = int(value) if value else 0
                    elif header == "Failure Count":
                        results["failures"] = int(value) if value else 0
                    elif header == "Average Response Time":
                        results["avg_response_time"] = float(value) if value else 0
                    elif header == "Requests/s":
                        results["rps"] = float(value) if value else 0
                    elif header == "95%":
                        results["p95"] = float(value) if value else 0
                    elif header == "99%":
                        results["p99"] = float(value) if value else 0
                    elif header == "Min Response Time":
                        results["min_response_time"] = float(value) if value else 0
                    elif header == "Max Response Time":
                        results["max_response_time"] = float(value) if value else 0

                break

    except Exception as e:
        print(f"Ошибка парсинга CSV: {e}")

    return results


def run_all_scenarios(target: str, results_dir: Path):
    """Запуск всех сценариев для указанной цели."""
    all_results = {}

    for scenario_name in SCENARIOS.keys():
        results = run_locust_test(scenario_name, target, results_dir)
        all_results[f"{target}_{scenario_name}"] = results

        # Пауза между тестами
        print("\nОжидание 10 секунд перед следующим тестом...")
        time.sleep(10)

    return all_results


def compare_results(rest_results: dict, grpc_results: dict, results_dir: Path):
    """Сравнение результатов REST и gRPC."""
    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ REST vs gRPC")
    print("=" * 70)

    comparison = {}

    for scenario in SCENARIOS.keys():
        rest_key = f"rest_{scenario}"
        grpc_key = f"grpc_{scenario}"

        if rest_key in rest_results and grpc_key in grpc_results:
            rest = rest_results[rest_key]
            grpc = grpc_results[grpc_key]

            print(f"\n{SCENARIOS[scenario]['name']}:")
            print("-" * 50)

            # RPS сравнение
            rest_rps = rest.get("rps", 0)
            grpc_rps = grpc.get("rps", 0)
            print(f"  RPS:      REST: {rest_rps:.2f}  |  gRPC: {grpc_rps:.2f}")

            if rest_rps > 0:
                rps_diff = ((grpc_rps - rest_rps) / rest_rps) * 100
                print(f"            Разница: {rps_diff:+.1f}%")

            # Latency сравнение
            rest_avg = rest.get("avg_response_time", 0)
            grpc_avg = grpc.get("avg_response_time", 0)
            print(f"  Avg (ms): REST: {rest_avg:.2f}  |  gRPC: {grpc_avg:.2f}")

            if rest_avg > 0:
                avg_diff = ((grpc_avg - rest_avg) / rest_avg) * 100
                print(f"            Разница: {avg_diff:+.1f}%")

            # p95 сравнение
            rest_p95 = rest.get("p95", 0)
            grpc_p95 = grpc.get("p95", 0)
            print(f"  p95 (ms): REST: {rest_p95:.2f}  |  gRPC: {grpc_p95:.2f}")

            # Ошибки
            rest_err = rest.get("failures", 0)
            grpc_err = grpc.get("failures", 0)
            print(f"  Ошибок:   REST: {rest_err}  |  gRPC: {grpc_err}")

            comparison[scenario] = {
                "rest": rest,
                "grpc": grpc,
                "rps_difference_percent": rps_diff if rest_rps > 0 else 0,
                "latency_difference_percent": avg_diff if rest_avg > 0 else 0
            }

    # Сохранение сравнения
    comparison_file = results_dir / "comparison.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Сравнение сохранено в: {comparison_file}")

    return comparison


def main():
    parser = argparse.ArgumentParser(
        description="Запуск нагрузочных тестов для глоссария",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python run_tests.py --scenario sanity --target rest
  python run_tests.py --scenario stress --target grpc
  python run_tests.py --scenario all --target both
  python run_tests.py --scenario normal --target rest --web
        """
    )

    parser.add_argument(
        "--scenario", "-s",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="sanity",
        help="Сценарий тестирования (default: sanity)"
    )

    parser.add_argument(
        "--target", "-t",
        choices=["rest", "grpc", "both"],
        default="rest",
        help="Цель тестирования (default: rest)"
    )

    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Запуск с веб-интерфейсом Locust"
    )

    parser.add_argument(
        "--users", "-u",
        type=int,
        help="Переопределить количество пользователей"
    )

    parser.add_argument(
        "--spawn-rate", "-r",
        type=int,
        help="Переопределить скорость создания пользователей"
    )

    parser.add_argument(
        "--run-time",
        type=str,
        help="Переопределить время выполнения (например, '5m', '30s')"
    )

    args = parser.parse_args()

    # Переопределение параметров сценариев
    if args.users or args.spawn_rate or args.run_time:
        for scenario in SCENARIOS.values():
            if args.users:
                scenario["users"] = args.users
            if args.spawn_rate:
                scenario["spawn_rate"] = args.spawn_rate
            if args.run_time:
                scenario["run_time"] = args.run_time

    # Создание директории результатов
    results_dir = create_results_dir()
    print(f"Результаты будут сохранены в: {results_dir}")

    # Проверка наличия locustfile
    script_dir = os.path.dirname(os.path.abspath(__file__))

    headless = not args.web

    # Запуск тестов
    all_results = {}

    if args.target in ["rest", "both"]:
        locustfile = os.path.join(script_dir, TARGETS["rest"]["locustfile"])
        if not os.path.exists(locustfile):
            print(f"Ошибка: файл {locustfile} не найден")
            sys.exit(1)

        if args.scenario == "all":
            all_results.update(run_all_scenarios("rest", results_dir))
        else:
            result = run_locust_test(args.scenario, "rest", results_dir, headless)
            all_results[f"rest_{args.scenario}"] = result

    if args.target in ["grpc", "both"]:
        locustfile = os.path.join(script_dir, TARGETS["grpc"]["locustfile"])
        if not os.path.exists(locustfile):
            print(f"Ошибка: файл {locustfile} не найден")
            sys.exit(1)

        # Проверка наличия скомпилированных proto файлов
        pb2_file = os.path.join(script_dir, "glossary_pb2.py")
        if not os.path.exists(pb2_file):
            print("Proto файлы не скомпилированы. Запустите: python compile_proto.py")
            sys.exit(1)

        if args.scenario == "all":
            all_results.update(run_all_scenarios("grpc", results_dir))
        else:
            result = run_locust_test(args.scenario, "grpc", results_dir, headless)
            all_results[f"grpc_{args.scenario}"] = result

    # Сравнение результатов
    if args.target == "both" and args.scenario == "all":
        rest_results = {k: v for k, v in all_results.items() if k.startswith("rest_")}
        grpc_results = {k: v for k, v in all_results.items() if k.startswith("grpc_")}
        compare_results(rest_results, grpc_results, results_dir)

    # Сохранение общих результатов
    summary_file = results_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Все тесты завершены!")
    print(f"  Итоговый отчёт: {summary_file}")


if __name__ == "__main__":
    main()
