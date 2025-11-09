# SPBE Parser - Парсер данных СПБ Биржи

Парсер для сбора данных по облигациям с сайта СПБ Биржи (https://spbexchange.ru/).

## Описание

Проект включает два основных парсера:

1. **Парсер референсных данных** (`spbe_parser.py`) - собирает подробную информацию о всех облигациях
2. **Парсер проспектов** (`spbe_prospectus_parser.py`) - скачивает PDF проспекты для облигаций

## Требования

- Python 3.8+
- Google Chrome или Chromium (для Selenium)
- Docker (опционально, для упрощенного запуска)

## Установка

### Вариант 1: Локальная установка

#### Шаг 1: Установите Google Chrome

**Для Ubuntu/Debian:**
```bash
# Автоматическая установка с помощью скрипта
./install_chrome.sh

# Или вручную:
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f
```

**Для CentOS/RHEL/Fedora:**
```bash
sudo yum install -y google-chrome-stable
```

**Для macOS:**
```bash
brew install --cask google-chrome
```

**Для Windows:**
Скачайте и установите Chrome с https://www.google.com/chrome/

#### Шаг 2: Установите Python зависимости

```bash
pip install -r requirements.txt
```

### Вариант 2: Использование Docker (рекомендуется)

Docker автоматически устанавливает все зависимости, включая Chrome.

**Сборка образа:**
```bash
docker-compose build
```

**Запуск:**
```bash
# Оба парсера
docker-compose run spbe-parser --all

# Только референсные данные
docker-compose run spbe-parser --reference-data

# Только проспекты
docker-compose run spbe-parser --prospectuses
```

Результаты будут сохранены в локальные папки `output/` и `Prospectuses/`.

## Использование

### Запуск обоих парсеров

```bash
python main.py --all
```

### Запуск только парсера референсных данных

```bash
python main.py --reference-data
```

Результат: файл `SPBE_ReferenceData_YYYYMMDD.csv` с данными по всем облигациям.

### Запуск только парсера проспектов

```bash
python main.py --prospectuses
```

Результат: папка `Prospectuses/` со структурой:
```
Prospectuses/
├── Эмитент1/
│   └── ISIN1/
│       └── документы.pdf
├── Эмитент2/
│   └── ISIN2/
│       └── документы.pdf
...
```

### Дополнительные опции

#### Запуск с видимым браузером (для отладки)

```bash
python main.py --all --no-headless
```

#### Указать директорию для сохранения проспектов

```bash
python main.py --prospectuses --output-dir "My_Prospectuses"
```

## Структура проекта

```
SPBE_test/
├── main.py                        # Главный файл запуска
├── spbe_parser.py                 # Парсер референсных данных
├── spbe_prospectus_parser.py      # Парсер проспектов
├── requirements.txt               # Зависимости
├── README.md                      # Документация
└── SPBE_test.docx                 # Техническое задание
```

## Собираемые данные

### Референсные данные

Парсер собирает следующие поля (в английской нотации согласно ТЗ):

- ISIN
- Registration Number
- Security Category
- Security Identification Code
- CFI code assigned to the securities
- Series Number
- Face Value
- Face Value Currency
- Issue Size, pcs
- Issue Date
- Coupon
- Maturity Date
- Coupon Frequency
- Interest Payment Dates
- Current Coupon Information
- Redemption Amount
- Early Redemption Option
- Listing Section
- Decision date to include in the List
- Listing Inclusion Date
- Listing Exchange
- Start Date Organized Trading
- Available Trading Modes
- Instrument Group
- Lot Size
- Price Tick
- Price Quotation Units
- Settlement Currency
- Trading Restrictions
- Included in the exchange index universe
- Full Name Issuer
- Country Incorporation
- Issuer TIN
- Legal Address
- Information Issuer Default Events
- Information Issuer Technical Default Events
- Issuer's Investor Relations Website
- Foreign Exchange Disclosure Page
- Competent Authority/OAM Disclosure Page
- Annual Reports Disclosed Issuer

### Проспекты

Парсер скачивает:

1. **Для иностранных облигаций**:
   - Резюме проспекта ценных бумаг (PDF)
   - Структура: `Prospectuses/Эмитент/ISIN/файлы.pdf`

2. **Для РФ компаний**:
   - Все документы, относящиеся к облигациям
   - Включая аннулированные выпуски (при первом запуске)
   - Структура: `Prospectuses/Эмитент/ISIN/файлы.pdf`

## Расписание запуска (согласно ТЗ)

### Референсные данные
- **Время**: ежедневно ПН-ПТ в 23:55 МСК
- **Команда**: `python main.py --reference-data`

### Проспекты
- **Время**: ежедневно ПН-ПТ в 22:00 МСК
- **Команда**: `python main.py --prospectuses`

## Логирование

Все операции логируются в:
- Консоль (stdout)
- Файл `spbe_parser_YYYYMMDD.log`

Уровни логирования:
- `INFO` - общая информация о процессе
- `WARNING` - предупреждения (например, пропущенные элементы)
- `ERROR` - ошибки выполнения

## Особенности реализации

1. **Инкрементальное скачивание**: Парсер проспектов не скачивает файлы, которые уже существуют
2. **Обработка ошибок**: При ошибке обработки одной облигации, парсер продолжает работу с остальными
3. **Задержки между запросами**: Для предотвращения блокировки сайтом
4. **Очистка имен файлов**: Автоматическая замена недопустимых символов в именах директорий и файлов
5. **Headless режим**: По умолчанию браузер работает в фоновом режиме (можно отключить для отладки)

## Обработка специальных полей

Согласно ТЗ, некоторые поля обрабатываются особым образом:

- **Early Redemption Option**: "Предусмотрена" → "Yes", иначе → "No"
- **Trading Restrictions**: "Да" → "Yes", "Нет" → "No"
- **Included in the exchange index universe**: "Да" → "Yes", "нет" → "No"

## Устранение неполадок

### Ошибка "cannot find Chrome binary"

Эта ошибка означает, что Google Chrome не установлен или не найден в системе.

**Решение 1: Установите Chrome**
```bash
# Используйте скрипт автоматической установки
./install_chrome.sh

# Или установите вручную (см. секцию "Установка" выше)
```

**Решение 2: Используйте Docker**
```bash
docker-compose run spbe-parser --all
```

Docker уже содержит все необходимые зависимости, включая Chrome.

### Ошибка "WebDriver not found"

Убедитесь, что установлен Google Chrome. Драйвер скачивается автоматически через `webdriver-manager`.

Если проблема сохраняется:
```bash
# Очистите кэш webdriver-manager
rm -rf ~/.wdm

# Попробуйте снова
python main.py --all
```

### Timeout ошибки

Увеличьте время ожидания в коде или проверьте интернет-соединение.

Если сайт медленно отвечает, можно увеличить таймауты в файлах `spbe_parser.py` и `spbe_prospectus_parser.py`:
- Найдите строки с `time.sleep(...)` и увеличьте значения
- Увеличьте `timeout` параметр в методе `wait_for_element`

### Парсер не находит элементы

Возможно, структура сайта изменилась. Запустите с флагом `--no-headless` для визуальной отладки:

```bash
python main.py --all --no-headless
```

Это откроет видимое окно браузера и вы сможете увидеть, что происходит на каждом шаге.

### Проблемы с правами доступа

Если возникают ошибки с правами:

```bash
# Дайте права на выполнение скрипта установки
chmod +x install_chrome.sh

# Если проблемы с Selenium в Docker
docker-compose run --user root spbe-parser --all
```

## Автор

Реализовано согласно техническому заданию SPBE_test.docx

## Лицензия

Проект создан для внутреннего использования.
