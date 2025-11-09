#!/bin/bash

# Скрипт для установки Google Chrome на различных Linux дистрибутивах

set -e

echo "======================================"
echo "SPBE Parser - Установка Chrome"
echo "======================================"
echo ""

# Определяем ОС
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Не удалось определить ОС"
    exit 1
fi

echo "Обнаружена ОС: $OS"
echo ""

case "$OS" in
    ubuntu|debian)
        echo "Установка Chrome для Ubuntu/Debian..."

        # Скачиваем ключ Google
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

        # Добавляем репозиторий
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

        # Обновляем список пакетов
        sudo apt-get update

        # Устанавливаем Chrome
        sudo apt-get install -y google-chrome-stable

        echo "Chrome успешно установлен!"
        ;;

    centos|rhel|fedora)
        echo "Установка Chrome для CentOS/RHEL/Fedora..."

        # Создаем файл репозитория
        cat <<EOF | sudo tee /etc/yum.repos.d/google-chrome.repo
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

        # Устанавливаем Chrome
        sudo yum install -y google-chrome-stable

        echo "Chrome успешно установлен!"
        ;;

    *)
        echo "Неподдерживаемый дистрибутив: $OS"
        echo ""
        echo "Попробуйте установить Chrome вручную:"
        echo "1. Скачайте .deb пакет: wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
        echo "2. Установите: sudo dpkg -i google-chrome-stable_current_amd64.deb"
        echo "3. Исправьте зависимости: sudo apt-get install -f"
        echo ""
        echo "Или используйте Docker: docker-compose run spbe-parser --all"
        exit 1
        ;;
esac

# Проверяем установку
if command -v google-chrome &> /dev/null; then
    echo ""
    echo "======================================"
    echo "✓ Chrome установлен успешно!"
    echo "Версия: $(google-chrome --version)"
    echo "======================================"
    echo ""
    echo "Теперь вы можете запустить парсер:"
    echo "python main.py --all"
else
    echo ""
    echo "✗ Ошибка: Chrome не установлен"
    exit 1
fi
