"""
SPBE Reference Data Parser
Парсер для сбора референсных данных по облигациям с сайта СПБ Биржи
Использует Playwright + Firefox
"""

import logging
import time
import csv
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

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
        self.playwright = None
        self.browser = None
        self.page = None

    def setup_browser(self):
        """Настройка и запуск браузера"""
        logger.info("Запуск Firefox через Playwright...")
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.firefox.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )

        # Создаем контекст с игнорированием SSL ошибок
        context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            ignore_https_errors=True  # Игнорируем ошибки SSL сертификатов
        )

        self.page = context.new_page()

        # Увеличиваем таймаут по умолчанию
        self.page.set_default_timeout(30000)

        logger.info("Браузер Firefox успешно запущен")

    def close_browser(self):
        """Закрытие браузера"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Браузер закрыт")

    def get_bonds_list(self) -> List[Dict]:
        """
        Получение списка всех облигаций

        Returns:
            Список словарей с информацией об облигациях
        """
        logger.info("Получение списка облигаций...")

        # Переходим на страницу списка ценных бумаг БЕЗ фильтра
        # Фильтр применим через UI, так как URL параметры не работают
        bonds_url = f"{self.BONDS_LIST_URL}"
        logger.info(f"Переход на URL: {bonds_url}")
        self.page.goto(bonds_url, wait_until='domcontentloaded')

        # Ждем появления спиннера и затем его исчезновения
        try:
            # Сначала ждем появления спиннера (это значит страница начала загружаться)
            self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='attached', timeout=5000)
            logger.info("Спиннер загрузки появился")
        except:
            logger.info("Спиннер загрузки не появился (возможно страница уже загружена)")

        # Теперь ждем исчезновения спиннера
        try:
            self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='detached', timeout=30000)
            logger.info("Спиннер загрузки исчез")
        except:
            logger.warning("Спиннер не исчез в течение таймаута")

        # Ждем загрузки таблицы с данными
        try:
            self.page.wait_for_selector('.Table_root__2EkV0', timeout=10000)
            logger.info("Таблица найдена")
        except:
            logger.warning("Таблица не найдена")

        # Применяем фильтр "Облигации" через UI
        try:
            logger.info("Применяем фильтр 'Облигации' через UI...")

            # Кликаем на кнопку фильтра
            filter_button = self.page.query_selector('button svg[viewBox="0 0 20 20"] path[d*="M3.6 3h12.8"]')
            if filter_button:
                filter_button_parent = filter_button.evaluate('element => element.closest("button")')
                if filter_button_parent:
                    self.page.evaluate('element => element.click()', filter_button_parent)
                    logger.info("Кликнули на кнопку фильтра")
                    time.sleep(2)

            # Ищем и кликаем чекбокс "Облигации"
            # Пробуем найти текст "Облигации" и кликнуть на связанный чекбокс
            checkboxes = self.page.query_selector_all('input[type="checkbox"]')
            for checkbox in checkboxes:
                # Получаем родительский элемент и ищем текст рядом
                parent = checkbox.evaluate('element => element.closest("label") || element.parentElement')
                if parent:
                    parent_text = self.page.evaluate('element => element.textContent', parent)
                    if 'Облигаци' in parent_text:
                        logger.info(f"Найден чекбокс с текстом: {parent_text}")
                        checkbox.check()
                        logger.info("Применили фильтр 'Облигации'")
                        time.sleep(3)
                        break
            else:
                logger.warning("Не удалось найти чекбокс 'Облигации'")

        except Exception as e:
            logger.error(f"Ошибка при применении фильтра: {e}")
            # Продолжаем работу, парсим что есть

        # Дополнительное ожидание для полной загрузки данных после фильтрации
        time.sleep(5)

        bonds = []
        page = 0
        max_pages = 100  # Ограничение для безопасности

        while page < max_pages:
            logger.info(f"Обработка страницы {page + 1}...")

            # Ищем все ссылки в таблице, которые ведут на card_bond
            bond_links = self.page.query_selector_all('a[href*="card_bond"]')

            if not bond_links:
                logger.info("Ссылки с 'card_bond' не найдены, пробуем альтернативный метод")
                # Ищем все ссылки с параметром issue
                all_links = self.page.query_selector_all('a[href*="?issue="]')
                # Фильтруем только те, которые содержат card_bond в href
                bond_links = [link for link in all_links if 'card_bond' in (link.get_attribute('href') or '')]

            if not bond_links:
                logger.warning("Облигации не найдены на странице. Сохраняю HTML для отладки...")
                # Сохраняем HTML страницы для отладки
                html_content = self.page.content()
                with open(f'debug_page_{page}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"HTML сохранен в debug_page_{page}.html")

                # Также сохраним скриншот
                self.page.screenshot(path=f'debug_page_{page}.png')
                logger.info(f"Скриншот сохранен в debug_page_{page}.png")
                break

            # Собираем уникальные ссылки и коды
            page_bonds = []
            seen_links = set()

            for link in bond_links:
                href = link.get_attribute('href')
                if href and href not in seen_links:
                    seen_links.add(href)
                    # Формируем полный URL если нужно
                    if not href.startswith('http'):
                        href = self.BASE_URL + href
                    # Извлекаем issue ID из URL
                    issue_id = href.split('issue=')[-1].split('&')[0] if 'issue=' in href else None
                    if issue_id and issue_id.isdigit():
                        page_bonds.append({
                            'url': href,
                            'issue_id': issue_id
                        })

            logger.info(f"Найдено облигаций на странице: {len(page_bonds)}")
            bonds.extend(page_bonds)

            # Пробуем перейти на следующую страницу
            # Используем клик по кнопке "следующая страница" вместо перехода по URL
            page += 1
            logger.info(f"Переход на страницу {page + 1}...")

            # Ищем и кликаем кнопку "Next"
            next_button = self.page.query_selector('button.Pagination_paginationButtonNext__7dYko')
            if not next_button:
                logger.info("Кнопка 'Следующая страница' не найдена, достигнут конец списка")
                break

            # Проверяем, активна ли кнопка (не disabled)
            is_disabled = next_button.evaluate('element => element.disabled')
            if is_disabled:
                logger.info("Кнопка 'Следующая страница' неактивна, достигнут конец списка")
                break

            try:
                # Кликаем на кнопку "Next"
                next_button.click()
                logger.info("Кликнули на кнопку 'Следующая страница'")

                # Ждем загрузки новых данных
                try:
                    self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='attached', timeout=3000)
                    self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='detached', timeout=30000)
                except:
                    pass

                time.sleep(3)

                # Проверяем, есть ли облигации на новой странице
                test_links = self.page.query_selector_all('a[href*="card_bond"]')
                if not test_links:
                    logger.info("На следующей странице облигации не найдены, завершаем")
                    break
            except Exception as e:
                logger.info(f"Ошибка при переходе на страницу {page}: {e}")
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

        try:
            self.page.goto(bond_url, wait_until='networkidle', timeout=30000)
        except PlaywrightTimeoutError:
            logger.error(f"Timeout при загрузке страницы {bond_url}")
            return {}

        time.sleep(3)  # Ждем загрузки динамического контента

        bond_data = {}

        try:
            # Ждем загрузки полей
            self.page.wait_for_selector('li.SecuritiesField_item__7TKJg', timeout=10000)

            # Ищем все элементы с классом SecuritiesField_item
            fields = self.page.query_selector_all('li.SecuritiesField_item__7TKJg')

            for field in fields:
                try:
                    # Получаем название поля
                    title_element = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
                    if not title_element:
                        continue

                    title = title_element.inner_text().strip()

                    # Убираем ссылки на footnotes
                    if '[' in title:
                        title = title.split('[')[0].strip()

                    # Получаем значение поля
                    desc_element = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
                    if not desc_element:
                        continue

                    # Проверяем наличие ссылок
                    links = desc_element.query_selector_all('a')
                    if links:
                        value = ' | '.join([link.get_attribute('href') or link.inner_text() for link in links])
                    else:
                        value = desc_element.inner_text().strip()

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

            logger.info(f"Облигация успешно обработана. Получено полей: {len(bond_data)}")

        except PlaywrightTimeoutError:
            logger.error(f"Timeout при ожидании элементов на странице {bond_url}")
        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей облигации: {e}")

        return bond_data

    def parse_all_bonds(self) -> List[Dict]:
        """
        Парсинг всех облигаций

        Returns:
            Список словарей с данными всех облигаций
        """
        self.setup_browser()

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
            self.close_browser()

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
