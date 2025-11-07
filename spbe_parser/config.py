"""
Configuration and field mappings for SPBE parser
"""

import os
from datetime import datetime
from typing import Dict

# Base URLs
SPBE_BASE_URL = "https://spbexchange.ru"
SPBE_SECURITIES_LIST_URL = f"{SPBE_BASE_URL}/listing/securities/list/"
SPBE_ISSUERS_URL = "https://issuers.spbexchange.ru/"

# Output paths
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
PROSPECTUSES_DIR = os.path.join(OUTPUT_DIR, "Prospectuses")
REFERENCE_DATA_DIR = OUTPUT_DIR

# Reference data file naming
def get_reference_data_filename() -> str:
    """Generate filename for reference data with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"SPBE_ReferenceData_{date_str}.csv"

# Field mapping: Russian -> English
FIELD_MAPPING: Dict[str, str] = {
    "ISIN код": "ISIN",
    "Регистрационный номер": "Registration Number",
    "Вид, категория (тип) ценной бумаги": "Security Category",
    "Идентификационный код ценной бумаги": "Security Identification Code",
    "Международный код классификации финансовых инструментов (CFI), присвоенный ценным бумагам": "CFI code assigned to the securities",
    "Международный код классификации финансовых инструментов (CFI), присвоенный ценным бумагам на дату принятия решения о листинге ценных бумаг": "CFI code as of the listing decision date",
    "Номер серии": "Series Number",
    "Номинальная стоимость": "Face Value",
    "Валюта номинальной стоимости": "Face Value Currency",
    "Общее количество ценных бумаг в выпуске, шт.": "Issue Size, pcs",
    "Дата выпуска": "Issue Date",
    "Ставка купона": "Coupon",
    "Дата погашения": "Maturity Date",
    "Порядок выплаты процентов": "Coupon Frequency",
    "Даты выплаты процентов": "Interest Payment Dates",
    "Информация о размере текущего процента (купона) по облигациям (о порядке определения размера)": "Current Сoupon Information (calculation method)",
    "Сумма погашения": "Redemption Amount",
    "Указание на наличие возможности досрочного погашения облигаций": "Early Redemption Option",
    "Раздел Списка": "Listing Section",
    "Дата принятия решения о включении ценных бумаг в Список": "Decision date to include in the List",
    "Дата включения ценных бумаг в Список": "Listing Inclusion Date",
    "Биржа, на которой ценные бумаги эмитента прошли процедуру листинга": "Listing Exchange",
    "Дата начала организованных торгов": "Start Date Organized Trading",
    "Режимы торгов, в которых возможно заключение договоров": "Available Trading Modes",
    "Группа инструментов": "Instrument Group",
    "Лот": "Lot Size",
    "Шаг цены": "Price Tick",
    "Валюта цены": "Price Quotation Units",
    "Валюта расчетов": "Settlement Currency",
    "Указание на то, что ценные бумаги ограничены в обороте (в том числе предназначены для квалифицированных инвесторов)": "Trading Restrictions (incl. qualified investors)",
    "Указание на то, что ценные бумаги включены в базу расчета индексов организатора торговли": "Included in the exchange index universe",
    "Полное наименование эмитента": "Full Name Issuer",
    "Государство учреждения эмитента": "Country Incorporation",
    "Идентификационный номер налогоплательщика эмитента (при наличии)": "Issuer TIN",
    "Юридический адрес эмитента": "Legal Address",
    "Информация о фактах дефолта эмитента": "Information Issuer Default Events",
    "Информация о фактах технического дефолта эмитента": "Information Issuer Technical Default Events",
    "Адрес страницы сайта в сети Интернет, используемой для раскрытия информации для инвесторов": "Issuer's Investor Relations Website",
    "Адрес страницы иностранной биржи в сети Интернет, на которой раскрывается информация об эмитенте иностранных ценных бумаг и о ценных бумагах данного эмитента": "Foreign Exchange Disclosure Page",
    "Адрес страницы государственного органа, и/или уполномоченного лица в сети Интернет, на которой раскрывается информация об эмитенте иностранных ценных бумаг и о ценных бумагах данного эмитента": "Competent Authority/OAM Disclosure Page",
    "Годовые отчеты, раскрытые эмитентом": "Annual Reports Disclosed Issuer",
}

# Additional field for first payment date
ADDITIONAL_FIELDS = ["First Payment Date"]

# Coupon frequency mapping
COUPON_FREQUENCY_MAPPING: Dict[str, str] = {
    "один раз в полугодие в конце полугодия": "2",
    "раз в полугодие": "2",
    "полугодие": "2",
    "один раз в год": "1",
    "раз в год": "1",
    "ежегодно": "1",
    "год": "1",
    "квартал": "4",
    "ежеквартально": "4",
    "раз в квартал": "4",
    "месяц": "12",
    "ежемесячно": "12",
    "раз в месяц": "12",
}

# Boolean field mapping
BOOLEAN_MAPPING: Dict[str, str] = {
    "да": "Yes",
    "предусмотрена": "Yes",
    "предусмотрено": "Yes",
    "есть": "Yes",
    "нет": "No",
    "не предусмотрена": "No",
    "не предусмотрено": "No",
}

# Request settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # seconds between requests to avoid rate limiting
MAX_RETRIES = 3

# User agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
