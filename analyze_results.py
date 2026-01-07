#!/usr/bin/env python3
"""
Скрипт для анализа и визуализации результатов нагрузочного тестирования.

Анализирует CSV файлы, сгенерированные Locust, и создаёт:
- Сводные таблицы сравнения
- Графики производительности
- Markdown отчёт

Использование:
    python analyze_results.py --results-dir results/20240101_120000

Автор: VKR Project
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Фикс для Windows консоли
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


def load_csv_stats(csv_path: str) -> dict:
    """Загрузка статистики из CSV файла."""
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

    if lines is None:
        print(f"Не удалось прочитать {csv_path} ни в одной кодировке")
        return results

    try:

        if len(lines) < 2:
            return results

        headers = [h.strip('"') for h in lines[0].strip().split(",")]

        for line in lines[1:]:
            values = [v.strip('"') for v in line.strip().split(",")]

            if len(values) >= 2:
                request_type = values[0]
                name = values[1]

                row_data = {}
                for i, header in enumerate(headers):
                    if i < len(values):
                        row_data[header] = values[i]

                if name == "Aggregated":
                    results["aggregated"] = row_data
                else:
                    if "requests" not in results:
                        results["requests"] = []
                    results["requests"].append(row_data)

    except Exception as e:
        print(f"Ошибка парсинга {csv_path}: {e}")

    return results


def load_history_csv(csv_path: str) -> list:
    """Загрузка истории из CSV файла."""
    history = []

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

    if lines is None:
        print(f"Не удалось прочитать {csv_path}")
        return history

    try:

        if len(lines) < 2:
            return history

        headers = [h.strip('"') for h in lines[0].strip().split(",")]

        for line in lines[1:]:
            values = [v.strip('"') for v in line.strip().split(",")]
            row = {}
            for i, header in enumerate(headers):
                if i < len(values):
                    try:
                        row[header] = float(values[i]) if values[i] else 0
                    except ValueError:
                        row[header] = values[i]
            history.append(row)

    except Exception as e:
        print(f"Ошибка загрузки {csv_path}: {e}")

    return history


def generate_markdown_report(results_dir: Path) -> str:
    """Генерация Markdown отчёта."""
    report = []
    report.append("# Отчёт о нагрузочном тестировании\n")
    report.append(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Директория результатов:** `{results_dir}`\n\n")

    # Загрузка summary.json если есть
    summary_file = results_dir / "summary.json"
    if summary_file.exists():
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        report.append("## Сводка результатов\n\n")

        # Таблица результатов
        report.append("| Сценарий | Цель | Запросов | Ошибок | RPS | Avg (ms) | p95 (ms) | p99 (ms) |\n")
        report.append("|----------|------|----------|--------|-----|----------|----------|----------|\n")

        for test_name, data in summary.items():
            if isinstance(data, dict) and "total_requests" in data:
                parts = test_name.split("_")
                target = parts[0] if parts else "N/A"
                scenario = "_".join(parts[1:]) if len(parts) > 1 else "N/A"

                report.append(
                    f"| {scenario} | {target.upper()} | "
                    f"{data.get('total_requests', 'N/A')} | "
                    f"{data.get('failures', 'N/A')} | "
                    f"{data.get('rps', 0):.2f} | "
                    f"{data.get('avg_response_time', 0):.2f} | "
                    f"{data.get('p95', 'N/A')} | "
                    f"{data.get('p99', 'N/A')} |\n"
                )

        report.append("\n")

    # Загрузка comparison.json если есть
    comparison_file = results_dir / "comparison.json"
    if comparison_file.exists():
        with open(comparison_file, "r", encoding="utf-8") as f:
            comparison = json.load(f)

        report.append("## Сравнение REST vs gRPC\n\n")

        for scenario, data in comparison.items():
            report.append(f"### {scenario.replace('_', ' ').title()}\n\n")

            rest = data.get("rest", {})
            grpc = data.get("grpc", {})

            report.append("| Метрика | REST | gRPC | Разница |\n")
            report.append("|---------|------|------|--------|\n")

            # RPS
            rest_rps = rest.get("rps", 0)
            grpc_rps = grpc.get("rps", 0)
            diff = data.get("rps_difference_percent", 0)
            report.append(f"| RPS | {rest_rps:.2f} | {grpc_rps:.2f} | {diff:+.1f}% |\n")

            # Avg Response Time
            rest_avg = rest.get("avg_response_time", 0)
            grpc_avg = grpc.get("avg_response_time", 0)
            diff = data.get("latency_difference_percent", 0)
            report.append(f"| Avg (ms) | {rest_avg:.2f} | {grpc_avg:.2f} | {diff:+.1f}% |\n")

            # p95
            rest_p95 = rest.get("p95", 0)
            grpc_p95 = grpc.get("p95", 0)
            report.append(f"| p95 (ms) | {rest_p95} | {grpc_p95} | - |\n")

            # Errors
            rest_err = rest.get("failures", 0)
            grpc_err = grpc.get("failures", 0)
            report.append(f"| Ошибок | {rest_err} | {grpc_err} | - |\n")

            report.append("\n")

    # Поиск и анализ индивидуальных CSV файлов
    csv_files = list(results_dir.glob("*_stats.csv"))
    if csv_files:
        report.append("## Детальная статистика по эндпоинтам\n\n")

        for csv_file in sorted(csv_files):
            test_name = csv_file.stem.replace("_stats", "")
            report.append(f"### {test_name}\n\n")

            stats = load_csv_stats(str(csv_file))
            if "requests" in stats:
                report.append("| Endpoint | Requests | Failures | Avg (ms) | Min (ms) | Max (ms) |\n")
                report.append("|----------|----------|----------|----------|----------|----------|\n")

                for req in stats["requests"]:
                    report.append(
                        f"| {req.get('Name', 'N/A')[:40]} | "
                        f"{req.get('Request Count', 'N/A')} | "
                        f"{req.get('Failure Count', 'N/A')} | "
                        f"{req.get('Average Response Time', 'N/A')} | "
                        f"{req.get('Min Response Time', 'N/A')} | "
                        f"{req.get('Max Response Time', 'N/A')} |\n"
                    )

            report.append("\n")

    # Выводы и рекомендации
    report.append("## Выводы\n\n")
    report.append("### Ключевые наблюдения\n\n")
    report.append("1. **Производительность REST API:**\n")
    report.append("   - [Заполните на основе результатов]\n\n")
    report.append("2. **Производительность gRPC:**\n")
    report.append("   - [Заполните на основе результатов]\n\n")
    report.append("3. **Сравнение:**\n")
    report.append("   - [Заполните на основе результатов]\n\n")

    report.append("### Рекомендации\n\n")
    report.append("1. [Добавьте рекомендации на основе результатов]\n")
    report.append("2. [Добавьте рекомендации на основе результатов]\n\n")

    report.append("### Ограничения тестирования\n\n")
    report.append("1. Тестирование проводилось на локальной машине\n")
    report.append("2. База данных SQLite (однопоточная)\n")
    report.append("3. Один экземпляр сервера\n\n")

    return "".join(report)


def create_simple_charts(results_dir: Path):
    """Создание простых текстовых графиков (без matplotlib)."""
    summary_file = results_dir / "summary.json"

    if not summary_file.exists():
        print("Файл summary.json не найден")
        return

    with open(summary_file, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # ASCII график RPS
    print("\n" + "=" * 60)
    print("ГРАФИК RPS (Requests Per Second)")
    print("=" * 60)

    max_rps = 0
    rps_data = []

    for test_name, data in summary.items():
        if isinstance(data, dict) and "rps" in data:
            rps = data.get("rps", 0)
            rps_data.append((test_name, rps))
            if rps > max_rps:
                max_rps = rps

    if max_rps > 0:
        scale = 50 / max_rps
        for name, rps in sorted(rps_data, key=lambda x: x[1], reverse=True):
            bar = "█" * int(rps * scale)
            print(f"{name:30} | {bar} {rps:.2f}")

    # ASCII график Latency
    print("\n" + "=" * 60)
    print("ГРАФИК LATENCY (Average Response Time, ms)")
    print("=" * 60)

    max_latency = 0
    latency_data = []

    for test_name, data in summary.items():
        if isinstance(data, dict) and "avg_response_time" in data:
            latency = data.get("avg_response_time", 0)
            latency_data.append((test_name, latency))
            if latency > max_latency:
                max_latency = latency

    if max_latency > 0:
        scale = 50 / max_latency
        for name, latency in sorted(latency_data, key=lambda x: x[1]):
            bar = "█" * int(latency * scale)
            print(f"{name:30} | {bar} {latency:.2f} ms")


def main():
    parser = argparse.ArgumentParser(
        description="Анализ результатов нагрузочного тестирования"
    )

    parser.add_argument(
        "--results-dir", "-r",
        type=str,
        help="Директория с результатами тестов"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="REPORT.md",
        help="Имя выходного файла отчёта (default: REPORT.md)"
    )

    parser.add_argument(
        "--charts",
        action="store_true",
        help="Показать ASCII графики"
    )

    args = parser.parse_args()

    # Определение директории результатов
    if args.results_dir:
        results_dir = Path(args.results_dir)
    else:
        # Поиск последней директории результатов
        results_base = Path("results")
        if results_base.exists():
            subdirs = sorted([d for d in results_base.iterdir() if d.is_dir()])
            if subdirs:
                results_dir = subdirs[-1]
                print(f"Используется последняя директория: {results_dir}")
            else:
                print("Директории с результатами не найдены в 'results/'")
                sys.exit(1)
        else:
            print("Директория 'results/' не существует")
            sys.exit(1)

    if not results_dir.exists():
        print(f"Директория {results_dir} не существует")
        sys.exit(1)

    print(f"Анализ результатов из: {results_dir}")

    # ASCII графики
    if args.charts:
        create_simple_charts(results_dir)

    # Генерация отчёта
    report = generate_markdown_report(results_dir)

    output_path = results_dir / args.output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✓ Отчёт сохранён: {output_path}")


if __name__ == "__main__":
    main()
