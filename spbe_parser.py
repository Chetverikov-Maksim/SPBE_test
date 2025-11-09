"""
SPBE Reference Data Parser
Парсер для сбора референсных данных по облигациям с сайта СПБ Биржи
"""

import logging
import time
import csv
from datetime import datetime
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SPBEParser:
    """Парсер для сайта СПБ Биржи"""

    BASE_URL = "https://spbexchange.ru"
    BONDS_LIST_URL = f"{BASE_URL}/listing/securities/list/"

    # Маппинг русских полей на английские (из ТЗ)
    FIELD_MAPPING = {
        'ISIN код': 'ISIN',
        'Регистрационный номер': 'Registration Number',
        'Вид, категория (тип) ценной бумаги': 'Security Category',
        'Идентификационный код ценной бумаги': 'Security Identification Code',
        'Международный код классификации финансовых инструментов (CFI), присвоенный ценным бумагам': 'CFI code assigned to the securities',
        'Международный код классификации финансовых инструментов (CFI), присвоенный ценным бумагам на дату принятия решения о листинге ценных бумаг': 'CFI code as of the listing decision date',
        'Номер серии': 'Series Number',
        'Номинальная стоимость': 'Face Value',
        'Валюта номинальной стоимости': 'Face Value Currency',
        'Общее количество ценных бумаг в выпуске, шт.': 'Issue Size, pcs',
        'Дата выпуска': 'Issue Date',
        'Ставка купона': 'Coupon',
        'Дата погашения': 'Maturity Date',
        'Порядок выплаты процентов': 'Coupon Frequency',
        'Даты выплаты процентов': 'Interest Payment Dates',
        'Информация о размере текущего процента (купона) по облигациям (о порядке определения размера)': 'Current Coupon Information (calculation method)',
        'Сумма погашения': 'Redemption Amount',
        'Указание на наличие возможности досрочного погашения облигаций': 'Early Redemption Option',
        'Раздел Списка': 'Listing Section',
        'Дата принятия решения о включении ценных бумаг в Список': 'Decision date to include in the List',
        'Дата включения ценных бумаг в Список': 'Listing Inclusion Date',
        'Биржа, на которой ценные бумаги эмитента прошли процедуру листинга': 'Listing Exchange',
        'Дата начала организованных торгов': 'Start Date Organized Trading',
        'Режимы торгов, в которых возможно заключение договоров': 'Available Trading Modes',
        'Группа инструментов': 'Instrument Group',
        'Лот': 'Lot Size',
        'Шаг цены': 'Price Tick',
        'Валюта цены': 'Price Quotation Units',
        'Валюта расчетов': 'Settlement Currency',
        'Указание на то, что ценные бумаги ограничены в обороте (в том числе предназначены для квалифицированных инвесторов)': 'Trading Restrictions (incl. qualified investors)',
        'Указание на то, что ценные бумаги включены в базу расчета индексов организатора торговли': 'Included in the exchange index universe',
        'Полное наименование эмитента': 'Full Name Issuer',
        'Государство учреждения эмитента': 'Country Incorporation',
        'Идентификационный номер налогоплательщика эмитента (при наличии)': 'Issuer TIN',
        'Юридический адрес эмитента': 'Legal Address',
        'Информация о фактах дефолта эмитента': 'Information Issuer Default Events',
        'Информация о фактах технического дефолта эмитента': 'Information Issuer Technical Default Events',
        'Адрес страницы сайта в сети Интернет, используемой для раскрытия информации для инвесторов': 'Issuer\'s Investor Relations Website',
        'Адрес страницы иностранной биржи в сети Интернет, на которой раскрывается информация об эмитенте иностранных ценных бумаг и о ценных бумагах данного эмитента': 'Foreign Exchange Disclosure Page',
        'Адрес страницы государственного органа, и/или уполномоченного лица в сети Интернет, на которой раскрывается информация об эмитенте иностранных ценных бумаг и о ценных бумагах данного эмитента': 'Competent Authority/OAM Disclosure Page',
        'Годовые отчеты, раскрытые эмитентом': 'Annual Reports Disclosed Issuer',
    }

    def __init__(self, headless: bool = True):
        """
        Инициализация парсера

        Args:
            headless: Запускать браузер в headless режиме
        """
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Настройка и запуск веб-драйвера"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        logger.info("Веб-драйвер успешно настроен")

    def close_driver(self):
        """Закрытие веб-драйвера"""
        if self.driver:
            self.driver.quit()
            logger.info("Веб-драйвер закрыт")

    def wait_for_element(self, by: By, value: str, timeout: int = 20) -> Optional[any]:
        """
        Ожидание появления элемента на странице

        Args:
            by: Тип поиска элемента
            value: Значение для поиска
            timeout: Время ожидания в секундах

        Returns:
            Элемент или None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Элемент не найден: {by}={value}")
            return None

    def get_bonds_list(self) -> List[Dict]:
        """
        Получение списка всех облигаций

        Returns:
            Список словарей с информацией об облигациях
        """
        logger.info("Получение списка облигаций...")

        # Формируем URL с фильтром "Облигации"
        bonds_url = f"{self.BONDS_LIST_URL}?page=0&size=10&sortBy=securityKind&sortByDirection=desc&securityKind=Облигации"
        self.driver.get(bonds_url)

        time.sleep(3)  # Ждем загрузки страницы

        bonds = []
        page = 0

        while True:
            logger.info(f"Обработка страницы {page + 1}...")

            # Ждем загрузки таблицы
            time.sleep(2)

            try:
                # Ищем ссылки на детальные страницы облигаций
                # На сайте ссылки на облигации имеют вид /listing/securities/card_bond/?issue=XXXX
                bond_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/listing/securities/card_bond/"]')

                if not bond_links:
                    logger.info("Облигации не найдены на странице")
                    break

                # Собираем уникальные ссылки и коды
                page_bonds = []
                seen_links = set()

                for link in bond_links:
                    href = link.get_attribute('href')
                    if href and href not in seen_links:
                        seen_links.add(href)
                        # Извлекаем issue ID из URL
                        issue_id = href.split('issue=')[-1] if 'issue=' in href else None
                        if issue_id:
                            page_bonds.append({
                                'url': href,
                                'issue_id': issue_id
                            })

                logger.info(f"Найдено облигаций на странице: {len(page_bonds)}")
                bonds.extend(page_bonds)

                # Проверяем наличие кнопки "Следующая страница"
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="следующая"], button[aria-label*="next"]')
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(2)
                        page += 1
                    else:
                        break
                except NoSuchElementException:
                    # Пробуем другой способ - увеличиваем номер страницы в URL
                    page += 1
                    next_url = f"{self.BONDS_LIST_URL}?page={page}&size=10&sortBy=securityKind&sortByDirection=desc&securityKind=Облигации"
                    self.driver.get(next_url)
                    time.sleep(2)

                    # Проверяем, есть ли облигации на новой странице
                    test_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/listing/securities/card_bond/"]')
                    if not test_links:
                        break

            except Exception as e:
                logger.error(f"Ошибка при обработке страницы {page + 1}: {e}")
                break

        logger.info(f"Всего найдено облигаций: {len(bonds)}")
        return bonds

    def parse_bond_details(self, bond_url: str) -> Dict:
        """
        Парсинг детальной информации об облигации

        Args:
            bond_url: URL страницы облигации

        Returns:
            Словарь с данными об облигации
        """
        logger.info(f"Парсинг облигации: {bond_url}")

        self.driver.get(bond_url)
        time.sleep(3)  # Ждем загрузки страницы

        bond_data = {}

        try:
            # Ищем все элементы с классом SecuritiesField_item
            fields = self.driver.find_elements(By.CSS_SELECTOR, 'li.SecuritiesField_item__7TKJg')

            for field in fields:
                try:
                    # Получаем название поля
                    title_element = field.find_element(By.CSS_SELECTOR, 'h3.SecuritiesField_itemTitle__7dfHY div')
                    title = title_element.text.strip()

                    # Убираем ссылки на footnotes
                    if '[' in title:
                        title = title.split('[')[0].strip()

                    # Получаем значение поля
                    desc_element = field.find_element(By.CSS_SELECTOR, 'div.SecuritiesField_itemDesc__JZ7w7')

                    # Проверяем наличие ссылок
                    links = desc_element.find_elements(By.TAG_NAME, 'a')
                    if links:
                        value = ' | '.join([link.get_attribute('href') or link.text for link in links])
                    else:
                        value = desc_element.text.strip()

                    # Преобразуем русское название в английское
                    if title in self.FIELD_MAPPING:
                        english_field = self.FIELD_MAPPING[title]
                        bond_data[english_field] = value
                    else:
                        # Если нет в маппинге, сохраняем как есть
                        bond_data[title] = value

                except Exception as e:
                    logger.warning(f"Ошибка при парсинге поля: {e}")
                    continue

            # Обработка специальных полей согласно ТЗ

            # Early Redemption Option: Предусмотрена -> Yes, иначе -> No
            if 'Early Redemption Option' in bond_data:
                if bond_data['Early Redemption Option'] == 'Предусмотрена':
                    bond_data['Early Redemption Option'] = 'Yes'
                else:
                    bond_data['Early Redemption Option'] = 'No'

            # Trading Restrictions: Да -> Yes, Нет -> No
            if 'Trading Restrictions (incl. qualified investors)' in bond_data:
                if bond_data['Trading Restrictions (incl. qualified investors)'] == 'Да':
                    bond_data['Trading Restrictions (incl. qualified investors)'] = 'Yes'
                else:
                    bond_data['Trading Restrictions (incl. qualified investors)'] = 'No'

            # Included in the exchange index universe: Да -> Yes, Нет/нет -> No
            if 'Included in the exchange index universe' in bond_data:
                value = bond_data['Included in the exchange index universe'].lower()
                if value == 'да':
                    bond_data['Included in the exchange index universe'] = 'Yes'
                else:
                    bond_data['Included in the exchange index universe'] = 'No'

            # Парсинг Coupon Frequency - нужно будет создать маппинг
            # Пока оставляем как есть, позже можно будет доработать

            # Парсинг Interest Payment Dates - нужно будет создать отдельное поле First Payment Date
            # Пока оставляем как есть, позже можно будет доработать

            logger.info(f"Облигация успешно обработана. Получено полей: {len(bond_data)}")

        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей облигации: {e}")

        return bond_data

    def parse_all_bonds(self) -> List[Dict]:
        """
        Парсинг всех облигаций

        Returns:
            Список словарей с данными всех облигаций
        """
        self.setup_driver()

        try:
            # Получаем список всех облигаций
            bonds_list = self.get_bonds_list()

            # Парсим детали каждой облигации
            all_bonds_data = []

            for i, bond in enumerate(bonds_list, 1):
                logger.info(f"Обработка облигации {i}/{len(bonds_list)}")

                try:
                    bond_data = self.parse_bond_details(bond['url'])
                    if bond_data:
                        all_bonds_data.append(bond_data)
                except Exception as e:
                    logger.error(f"Ошибка при обработке облигации {bond['url']}: {e}")
                    continue

                # Небольшая задержка между запросами
                time.sleep(1)

            return all_bonds_data

        finally:
            self.close_driver()

    def save_to_csv(self, data: List[Dict], filename: str = None):
        """
        Сохранение данных в CSV файл

        Args:
            data: Список словарей с данными
            filename: Имя файла (если None, генерируется автоматически)
        """
        if not filename:
            current_date = datetime.now().strftime('%Y%m%d')
            filename = f'SPBE_ReferenceData_{current_date}.csv'

        if not data:
            logger.warning("Нет данных для сохранения")
            return

        # Собираем все уникальные ключи из всех записей
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        # Сортируем ключи для консистентности
        fieldnames = sorted(list(all_keys))

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Данные сохранены в файл: {filename}")
        logger.info(f"Всего записей: {len(data)}")


def main():
    """Основная функция запуска парсера"""
    logger.info("Запуск парсера референсных данных SPBE")

    parser = SPBEParser(headless=True)

    try:
        # Парсим все облигации
        bonds_data = parser.parse_all_bonds()

        # Сохраняем в CSV
        parser.save_to_csv(bonds_data)

        logger.info("Парсинг успешно завершен")

    except Exception as e:
        logger.error(f"Ошибка при выполнении парсинга: {e}", exc_info=True)


if __name__ == "__main__":
    main()
