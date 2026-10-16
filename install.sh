#!/bin/bash

echo "[*] Настройка ArcRay Widget..."

# Проверка наличия python3 и venv
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 не найден. Установите python3."
    exit 1
fi

# Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install PyQt6 psutil
fi

echo "[+] Установка завершена успешно!"
echo "[+] Для запуска используйте: .venv/bin/python3 arc-ray.py"
