#!/usr/bin/env python3
"""
Скрипт для компиляции Protocol Buffers файлов.

Генерирует Python классы из .proto файлов для использования
в нагрузочном тестировании gRPC сервиса.

Использование:
    python compile_proto.py

Автор: VKR Project
"""

import os
import subprocess
import sys


def compile_proto():
    """Компиляция .proto файлов в Python классы."""

    # Определяем пути
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proto_dir = os.path.join(script_dir, "proto")
    output_dir = script_dir

    # Проверяем наличие директории proto
    if not os.path.exists(proto_dir):
        print(f"Ошибка: директория {proto_dir} не найдена")
        sys.exit(1)

    # Находим все .proto файлы
    proto_files = [f for f in os.listdir(proto_dir) if f.endswith(".proto")]

    if not proto_files:
        print(f"Ошибка: .proto файлы не найдены в {proto_dir}")
        sys.exit(1)

    print(f"Найдено {len(proto_files)} .proto файл(ов)")

    # Компилируем каждый файл
    for proto_file in proto_files:
        proto_path = os.path.join(proto_dir, proto_file)
        print(f"Компиляция: {proto_file}")

        try:
            # Команда для компиляции
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"-I{proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                proto_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout:
                print(result.stdout)

            print(f"  ✓ {proto_file} скомпилирован успешно")

        except subprocess.CalledProcessError as e:
            print(f"  ✗ Ошибка при компиляции {proto_file}:")
            print(f"    {e.stderr}")
            sys.exit(1)

        except FileNotFoundError:
            print("Ошибка: grpc_tools не установлен")
            print("Установите: pip install grpcio-tools")
            sys.exit(1)

    # Проверяем сгенерированные файлы
    generated_files = [
        "glossary_pb2.py",
        "glossary_pb2_grpc.py"
    ]

    print("\nСгенерированные файлы:")
    for gf in generated_files:
        gf_path = os.path.join(output_dir, gf)
        if os.path.exists(gf_path):
            print(f"  ✓ {gf}")
        else:
            print(f"  ✗ {gf} - не найден")

    print("\n✓ Компиляция завершена успешно!")
    print(f"  Файлы сохранены в: {output_dir}")


if __name__ == "__main__":
    compile_proto()
