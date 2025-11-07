# SPBE Bond Data Parser

Парсер данных по облигациям с Санкт-Петербургской биржи (SPBE).

## Описание

Этот проект реализует парсинг данных по облигациям с сайта СПБ Биржи в соответствии с техническим заданием. Парсер состоит из трех основных модулей:

1. **Парсер референсных данных** - собирает детальную информацию по всем облигациям
2. **Парсер проспектов иностранных эмитентов** - скачивает проспекты для облигаций иностранных компаний
3. **Парсер проспектов российских эмитентов** - скачивает документы для облигаций российских компаний

## Структура проекта

```
SPBE_test/
├── spbe_parser/              # Основной пакет парсера
│   ├── __init__.py
│   ├── config.py             # Конфигурация и маппинг полей
│   ├── utils.py              # Вспомогательные функции
│   ├── reference_data_parser.py       # Парсер референсных данных
│   ├── foreign_prospectus_parser.py   # Парсер проспектов иностранных эмитентов
│   ├── russian_prospectus_parser.py   # Парсер проспектов российских эмитентов
│   └── main.py               # Главный скрипт запуска
├── output/                   # Директория для выходных файлов
│   ├── Prospectuses/         # Проспекты (структура: Эмитент/ISIN/*.pdf)
│   └── SPBE_ReferenceData_YYYY-MM-DD.csv  # CSV с референсными данными
├── requirements.txt          # Зависимости Python
└── README.md                 # Документация
```

## Установка

### Требования

- Python 3.7+
- pip

### Установка зависимостей

```bash
# Клонируйте репозиторий (если еще не клонирован)
git clone <repository-url>
cd SPBE_test

# Установите зависимости
pip install -r requirements.txt
```

## Использование

### Запуск всех парсеров

```bash
python -m spbe_parser.main --all
```

### Запуск отдельных парсеров

#### Референсные данные

Собирает информацию по всем облигациям и сохраняет в CSV файл.

```bash
python -m spbe_parser.main --reference-data
```

**Выход:** `output/SPBE_ReferenceData_YYYY-MM-DD.csv`

**Поля в CSV:**
- ISIN, Registration Number, Security Category, Security Identification Code
- CFI code, Series Number, Face Value, Face Value Currency
- Issue Size, Issue Date, Coupon, Maturity Date, Coupon Frequency
- Interest Payment Dates, First Payment Date
- Current Coupon Information, Redemption Amount, Early Redemption Option
- Listing Section, Decision date, Listing Inclusion Date, Listing Exchange
- Start Date Organized Trading, Available Trading Modes
- Instrument Group, Lot Size, Price Tick, Price Quotation Units, Settlement Currency
- Trading Restrictions, Included in index universe
- Full Name Issuer, Country Incorporation, Issuer TIN, Legal Address
- Information Default Events, Information Technical Default Events
- Investor Relations Website, Foreign Exchange Disclosure Page
- Competent Authority/OAM Disclosure Page, Annual Reports

#### Проспекты иностранных эмитентов

Скачивает проспекты для облигаций иностранных компаний.

```bash
python -m spbe_parser.main --foreign-prospectus
```

**Структура выходных файлов:**
```
output/Prospectuses/
└── [Название эмитента]/
    └── [ISIN]/
        └── [файлы PDF]
```

#### Проспекты российских эмитентов

Скачивает документы для облигаций российских компаний.

```bash
# Обычный запуск
python -m spbe_parser.main --russian-prospectus

# Первый запуск (включая аннулированные облигации)
python -m spbe_parser.main --russian-prospectus --include-cancelled
```

**Структура выходных файлов:** аналогична иностранным эмитентам.

#### Все проспекты

Запустить оба парсера проспектов:

```bash
python -m spbe_parser.main --prospectus
```

### Дополнительные опции

```bash
# Указать кастомный файл логов
python -m spbe_parser.main --all --log-file my_custom.log

# Отключить запись в файл логов (только вывод в консоль)
python -m spbe_parser.main --all --no-log-file

# Комбинация парсеров
python -m spbe_parser.main --reference-data --foreign-prospectus
```

### Просмотр справки

```bash
python -m spbe_parser.main --help
```

## Расписание запуска (согласно ТЗ)

### Референсные данные
- **Частота:** Ежедневно, ПН-ПТ
- **Время:** 23:55 МСК (3:55 PM US)
- **Команда:** `python -m spbe_parser.main --reference-data`

### Проспекты
- **Частота:** Ежедневно, ПН-ПТ
- **Время:** 22:00 МСК (3:00 PM US)
- **Команда:** `python -m spbe_parser.main --prospectus`

**Примечание:** Для первого запуска проспектов российских эмитентов используйте флаг `--include-cancelled`.

### Настройка через cron (Linux/Mac)

```bash
# Открыть crontab
crontab -e

# Добавить задачи (время в MSK, настройте под вашу временную зону)
# Проспекты в 22:00 МСК
0 22 * * 1-5 cd /path/to/SPBE_test && /usr/bin/python3 -m spbe_parser.main --prospectus

# Референсные данные в 23:55 МСК
55 23 * * 1-5 cd /path/to/SPBE_test && /usr/bin/python3 -m spbe_parser.main --reference-data
```

### Настройка через Windows Task Scheduler

1. Откройте Task Scheduler
2. Создайте новую задачу
3. В Triggers установите расписание
4. В Actions добавьте:
   - Program: `python`
   - Arguments: `-m spbe_parser.main --prospectus` (или другие опции)
   - Start in: путь к директории SPBE_test

## Конфигурация

Основные настройки находятся в `spbe_parser/config.py`:

- **URL адреса** - базовые URL для парсинга
- **Таймауты и retry** - настройки запросов
- **Маппинг полей** - соответствие русских и английских названий полей
- **Пути вывода** - куда сохранять результаты

## Логирование

Парсер автоматически создает файлы логов с подробной информацией о работе:

- По умолчанию: `output/spbe_parser_YYYYMMDD_HHMMSS.log`
- Уровень логирования: INFO
- Формат: timestamp - module - level - message

## Обработка ошибок

Парсер реализует следующие механизмы обработки ошибок:

1. **Retry механизм** - автоматические повторные попытки при сетевых ошибках (до 3 раз)
2. **Exponential backoff** - увеличивающаяся задержка между попытками
3. **Пропуск существующих файлов** - не скачивает уже загруженные документы
4. **Подробное логирование** - все ошибки записываются в лог с traceback

## Оптимизация

Парсер оптимизирован для скорости и эффективности:

- Использование эффективных селекторов BeautifulSoup
- Кеширование HTTP запросов
- Пропуск уже скачанных файлов
- Параллельная обработка (можно расширить в будущем)
- Минимальные задержки между запросами (1 секунда для предотвращения блокировки)

## Возможные проблемы и решения

### Блокировка со стороны сайта

Если парсер блокируется сайтом:
- Увеличьте `REQUEST_DELAY` в `config.py`
- Проверьте `USER_AGENT` в `config.py`

### Изменение структуры сайта

Если сайт изменил структуру HTML:
- Обновите селекторы в соответствующих парсерах
- Проверьте логи для определения проблемных мест

### Ошибки кодировки

CSV файлы сохраняются с кодировкой UTF-8-BOM для корректного отображения в Excel.

## Разработка

### Добавление новых полей

1. Добавьте маппинг в `FIELD_MAPPING` в `config.py`
2. При необходимости добавьте обработку в `utils.py`
3. Тестируйте на небольшой выборке

### Расширение функциональности

- Все парсеры наследуются от базовых классов в соответствующих модулях
- Используйте logger для отладки: `self.logger.debug("message")`
- Следуйте существующим паттернам обработки ошибок

## Лицензия

Proprietary

## Контакты

Для вопросов и предложений обращайтесь к команде разработки.
