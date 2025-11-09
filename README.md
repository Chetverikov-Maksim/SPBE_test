# SPBE Parser - Парсер данных СПБ Биржи

Парсер для сбора данных по облигациям с сайта СПБ Биржи (https://spbexchange.ru/).

## Описание

Проект включает два основных парсера:

1. **Парсер референсных данных** (`spbe_parser.py`) - собирает подробную информацию о всех облигациях
2. **Парсер проспектов** (`spbe_prospectus_parser.py`) - скачивает PDF проспекты для облигаций

## Требования

- Python 3.8+
- **Playwright** (автоматически скачивает Firefox)

## Установка

### Быстрая установка (2 команды)

```bash
# 1. Установите Python зависимости
pip install -r requirements.txt

# 2. Установите Firefox для Playwright
python -m playwright install firefox
```

**Готово!** Теперь можно запускать парсер.

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

1. **Playwright + Firefox**: Современный инструмент автоматизации браузера
   - Автоматическая загрузка браузера
   - Лучшая надежность и производительность
   - Не требует установки Chrome или ChromeDriver
2. **Инкрементальное скачивание**: Парсер проспектов не скачивает файлы, которые уже существуют
3. **Обработка ошибок**: При ошибке обработки одной облигации, парсер продолжает работу с остальными
4. **Задержки между запросами**: Для предотвращения блокировки сайтом
5. **Очистка имен файлов**: Автоматическая замена недопустимых символов в именах директорий и файлов
6. **Headless режим**: По умолчанию браузер работает в фоновом режиме (можно отключить для отладки)

## Обработка специальных полей

Согласно ТЗ, некоторые поля обрабатываются особым образом:

- **Early Redemption Option**: "Предусмотрена" → "Yes", иначе → "No"
- **Trading Restrictions**: "Да" → "Yes", "Нет" → "No"
- **Included in the exchange index universe**: "Да" → "Yes", "нет" → "No"

## Устранение неполадок

### Ошибка "Executable doesn't exist" или "Browser not found"

Эта ошибка означает, что Firefox для Playwright не установлен.

**Решение:**
```bash
# Установите Firefox для Playwright
python -m playwright install firefox

# Или установите все браузеры
python -m playwright install
```

### Ошибка "Download failed" при установке Firefox

Если у вас проблемы с доступом к серверам Playwright:

**Решение 1: Использовать прокси**
```bash
# Установка через прокси
export HTTPS_PROXY=http://your-proxy:port
python -m playwright install firefox
```

**Решение 2: Ручная установка**
Скачайте Firefox вручную и укажите путь в коде или используйте системный Firefox.

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

Это откроет видимое окно Firefox и вы сможете увидеть, что происходит на каждом шаге.

## Автор

Реализовано согласно техническому заданию SPBE_test.docx

## Лицензия

Проект создан для внутреннего использования.
