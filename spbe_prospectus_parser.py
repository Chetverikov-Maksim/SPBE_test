"""
SPBE Prospectus Parser
Парсер для скачивания проспектов облигаций с сайта СПБ Биржи
Использует Playwright + Firefox
"""

import logging
import time
import os
import requests
import warnings
from pathlib import Path
from typing import Dict, List, Set
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin, urlparse

# Отключаем SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SPBEProspectusParser:
    """Парсер для скачивания проспектов с сайта СПБ Биржи"""

    BASE_URL = "https://spbexchange.ru"
    BONDS_LIST_URL = f"{BASE_URL}/listing/securities/list/"
    ISSUERS_BASE_URL = "https://issuers.spbexchange.ru"

    def __init__(self, headless: bool = True, output_dir: str = "Prospectuses"):
        """
        Инициализация парсера

        Args:
            headless: Запускать браузер в headless режиме
            output_dir: Директория для сохранения проспектов
        """
        self.headless = headless
        self.output_dir = output_dir
        self.playwright = None
        self.browser = None
        self.page = None
        self.downloaded_files: Set[str] = set()

        # Создаем базовую директорию
        Path(output_dir).mkdir(exist_ok=True)

    def setup_browser(self):
        """Настройка и запуск браузера"""
        logger.info("Запуск браузера через Playwright...")
        self.playwright = sync_playwright().start()

        # Пытаемся использовать Chromium если Firefox недоступен
        try:
            self.browser = self.playwright.firefox.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            browser_name = "Firefox"
        except Exception as e:
            logger.warning(f"Firefox недоступен: {e}")
            logger.info("Переключаемся на Chromium...")
            # Ищем установленный Chromium
            possible_chromium_paths = [
                os.path.expanduser('~/.cache/ms-playwright/chromium-1194/chrome-linux/chrome'),
                '/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome',
            ]
            chromium_path = None
            for path in possible_chromium_paths:
                if os.path.exists(path):
                    chromium_path = path
                    logger.info(f"Найден Chromium: {chromium_path}")
                    break

            # Используем Chromium с минимальными зависимостями
            launch_args = {
                'headless': self.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--single-process',  # Предотвращаем крэши в headless режиме
                    '--no-zygote'
                ]
            }
            if chromium_path:
                launch_args['executable_path'] = chromium_path

            self.browser = self.playwright.chromium.launch(**launch_args)
            browser_name = "Chromium"

        # Создаем контекст с игнорированием SSL ошибок
        context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            ignore_https_errors=True  # Игнорируем ошибки SSL сертификатов
        )

        self.page = context.new_page()

        # Увеличиваем таймаут по умолчанию
        self.page.set_default_timeout(30000)

        logger.info(f"Браузер {browser_name} успешно запущен")

    def close_browser(self):
        """Закрытие браузера"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Браузер закрыт")

    def download_file(self, url: str, save_path: str) -> bool:
        """
        Скачивание файла по URL

        Args:
            url: URL файла
            save_path: Путь для сохранения

        Returns:
            True если файл успешно скачан
        """
        # Проверяем, не скачали ли мы уже этот файл
        if save_path in self.downloaded_files:
            logger.info(f"Файл уже скачан: {save_path}")
            return True

        # Проверяем, существует ли уже файл
        if os.path.exists(save_path):
            logger.info(f"Файл уже существует: {save_path}")
            self.downloaded_files.add(save_path)
            return True

        try:
            logger.info(f"Скачивание файла: {url}")
            response = requests.get(url, timeout=30, stream=True, verify=False)
            response.raise_for_status()

            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Сохраняем файл
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Файл успешно скачан: {save_path}")
            self.downloaded_files.add(save_path)
            return True

        except Exception as e:
            logger.error(f"Ошибка при скачивании файла {url}: {e}")
            return False

    def get_foreign_bonds(self) -> List[Dict]:
        """
        Получение списка облигаций иностранных эмитентов из таблицы

        Фильтрует облигации по колонке "Вид, категория (тип) ценной бумаги"
        в основной таблице, без захода на каждую страницу облигации.

        Returns:
            Список словарей с информацией об облигациях
        """
        logger.info("Получение списка облигаций иностранных эмитентов...")

        # Переходим на страницу списка БЕЗ параметров (параметры в URL не работают)
        bonds_url = self.BONDS_LIST_URL
        logger.info(f"Переход на URL: {bonds_url}")
        self.page.goto(bonds_url, wait_until='domcontentloaded')

        # Ждем исчезновения спиннера
        try:
            self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='detached', timeout=30000)
            logger.info("Спиннер загрузки исчез")
        except:
            logger.warning("Спиннер не исчез в течение таймаута")

        # Ждем загрузки таблицы
        try:
            self.page.wait_for_selector('.Table_root__2EkV0', timeout=10000)
            logger.info("Таблица найдена")
        except:
            logger.warning("Таблица не найдена")

        # Применяем фильтр "Облигации" через UI (копия логики из spbe_parser.py)
        try:
            logger.info("Применяем фильтр 'Облигации' через UI...")

            # Кликаем на кнопку фильтра
            filter_button_selector = 'button:has(svg path[d*="M3.6 3h12.8"])'
            filter_button = self.page.query_selector(filter_button_selector)

            if filter_button:
                filter_button.click()
                logger.info("Кликнули на кнопку фильтра")
                time.sleep(2)

                # Ищем dropdown "Вид ценной бумаги"
                security_type_input = self.page.query_selector('input[placeholder*="Выберите вид ценной бумаги"]')

                if security_type_input:
                    logger.info("Найден dropdown 'Вид ценной бумаги'")

                    # Кликаем на родительский div
                    parent_handle = security_type_input.evaluate_handle('element => element.closest(".Input_polygon__RXMrw")')
                    parent_div = parent_handle.as_element()
                    parent_div.click()
                    logger.info("Кликнули на dropdown")
                    time.sleep(1)

                    # Выбираем "Облигации"
                    options = self.page.locator('text="Облигации"').all()
                    for option in options:
                        if option.is_visible():
                            option.click()
                            logger.info("Выбрали 'Облигации' из dropdown")
                            break

                    # Кликаем "Сохранить"
                    apply_btn = self.page.locator('button:has-text("Сохранить")').first
                    if apply_btn.is_visible(timeout=1000):
                        apply_btn.click()
                        logger.info("Кликнули 'Сохранить'")
                        time.sleep(3)

        except Exception as e:
            logger.error(f"Ошибка при применении фильтра: {e}")

        # Дополнительное ожидание после фильтрации
        time.sleep(3)

        foreign_bonds = []

        # Получаем структуру таблицы один раз (заголовки)
        from bs4 import BeautifulSoup

        # Определяем индекс колонки категории (делаем один раз)
        category_idx = None
        try:
            page_html = self.page.content()
            soup = BeautifulSoup(page_html, 'html.parser')
            table = soup.find('table', class_='Table_display__szeQI')
            if table:
                thead = table.find('thead')
                if thead:
                    headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                    logger.info(f"Найдено колонок в таблице: {len(headers)}")
                    for idx, header in enumerate(headers):
                        if 'категория' in header.lower() or 'тип' in header.lower():
                            category_idx = idx
                            logger.info(f"Колонка категории найдена под индексом {idx}: '{header}'")
                            break
        except Exception as e:
            logger.error(f"Ошибка при получении структуры таблицы: {e}")

        if category_idx is None:
            logger.warning("Колонка с категорией не найдена, используем альтернативный метод")
            logger.info(f"Всего найдено иностранных облигаций: {len(foreign_bonds)}")
            return foreign_bonds

        # Парсим все страницы с пагинацией
        page_num = 0
        max_pages = 100  # Защита от бесконечного цикла

        while page_num < max_pages:
            logger.info(f"Парсинг страницы {page_num + 1}...")

            try:
                # Получаем HTML текущей страницы
                page_html = self.page.content()
                soup = BeautifulSoup(page_html, 'html.parser')

                # Находим таблицу
                table = soup.find('table', class_='Table_display__szeQI')
                if not table:
                    table = soup.find('table')

                if not table:
                    logger.warning(f"Таблица не найдена на странице {page_num + 1}")
                    break

                # Парсим строки таблицы
                tbody = table.find('tbody')
                if not tbody:
                    logger.warning(f"tbody не найден на странице {page_num + 1}")
                    break

                rows = tbody.find_all('tr')
                logger.info(f"Найдено строк на странице {page_num + 1}: {len(rows)}")

                for row_idx, row in enumerate(rows):
                    cells = row.find_all('td')

                    if len(cells) <= category_idx:
                        logger.debug(f"Строка {row_idx}: недостаточно колонок ({len(cells)})")
                        continue

                    # Проверяем категорию
                    category_cell = cells[category_idx]
                    category_text = category_cell.get_text(strip=True)

                    # Фильтруем только "иностранного эмитента"
                    if 'иностранного эмитента' in category_text.lower():

                        # Ищем ссылку в этой строке
                        link = row.find('a', href=True)
                        if link:
                            href = link.get('href', '')
                            logger.debug(f"Строка {row_idx}: найдена ссылка {href}")

                            if 'card_bond' in href:
                                if not href.startswith('http'):
                                    href = self.BASE_URL + href

                                issue_id = href.split('issue=')[-1] if 'issue=' in href else None

                                # ISIN обычно в первой колонке или в тексте ссылки
                                isin = link.get_text(strip=True)

                                if issue_id:
                                    # Получаем название эмитента из колонки 2 (индекс 2)
                                    issuer_name = None
                                    if len(cells) > 2:
                                        issuer_name = cells[2].get_text(strip=True)

                                    foreign_bonds.append({
                                        'url': href,
                                        'issue_id': issue_id,
                                        'isin': isin,
                                        'issuer_name': issuer_name,
                                        'category': category_text
                                    })
                                    logger.info(f"Найдена иностранная облигация: {isin} ({issuer_name}) - {category_text}")
                                else:
                                    logger.warning(f"Строка {row_idx}: issue_id не найден в {href}")
                            else:
                                logger.debug(f"Строка {row_idx}: ссылка не содержит 'card_bond': {href}")
                        else:
                            logger.warning(f"Строка {row_idx}: ссылка не найдена в строке с категорией 'иностранного эмитента'")

                # Переход на следующую страницу
                page_num += 1

                # Ищем кнопку "Next"
                next_button = self.page.query_selector('button.Pagination_paginationButtonNext__7dYko')
                if not next_button:
                    logger.info("Кнопка 'Следующая страница' не найдена, достигнут конец списка")
                    break

                # Проверяем, активна ли кнопка
                is_disabled = next_button.evaluate('element => element.disabled')
                if is_disabled:
                    logger.info("Кнопка 'Следующая страница' неактивна, достигнут конец списка")
                    break

                # Кликаем на кнопку "Next"
                next_button.click()
                logger.info(f"Переход на страницу {page_num + 1}...")

                # Ждем загрузки новых данных
                try:
                    self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='attached', timeout=3000)
                    self.page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='detached', timeout=30000)
                except:
                    pass

                time.sleep(2)

            except Exception as e:
                logger.error(f"Ошибка при парсинге страницы {page_num + 1}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                break

        logger.info(f"Всего найдено иностранных облигаций: {len(foreign_bonds)}")
        return foreign_bonds

    def download_foreign_prospectuses(self, bonds: List[Dict]):
        """
        Скачивание проспектов для иностранных облигаций

        Args:
            bonds: Список облигаций
        """
        logger.info("Скачивание проспектов для иностранных облигаций...")

        for i, bond in enumerate(bonds, 1):
            isin = bond.get('isin', f"bond_{i}")
            issuer_name = bond.get('issuer_name')
            logger.info(f"Обработка облигации {i}/{len(bonds)}: {isin} ({issuer_name})")

            try:
                self.page.goto(bond['url'], wait_until='networkidle', timeout=30000)
                time.sleep(2)

                # Ждем загрузки полей
                self.page.wait_for_selector('li.SecuritiesField_item__7TKJg', timeout=10000)

                # Если issuer_name не был получен ранее, получаем его сейчас
                if not issuer_name:
                    logger.info("issuer_name отсутствует, получаем из полей страницы...")
                    fields_for_issuer = self.page.query_selector_all('li.SecuritiesField_item__7TKJg')
                    for field in fields_for_issuer:
                        try:
                            title_elem = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
                            if title_elem and 'Полное наименование эмитента' in title_elem.inner_text():
                                desc_elem = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
                                if desc_elem:
                                    issuer_name = desc_elem.inner_text().strip()
                                    bond['issuer_name'] = issuer_name
                                    logger.info(f"Получено имя эмитента: {issuer_name}")
                                    break
                        except:
                            continue

                    if not issuer_name:
                        issuer_name = f"Unknown_Issuer_{isin}"
                        logger.warning(f"Не удалось получить имя эмитента, используем: {issuer_name}")

                # Ищем поле с резюме проспекта
                fields = self.page.query_selector_all('li.SecuritiesField_item__7TKJg')

                for field in fields:
                    try:
                        title_elem = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
                        if not title_elem:
                            continue

                        title = title_elem.inner_text().strip()

                        if 'Резюме проспекта ценных бумаг' in title:
                            # Ищем ссылку на PDF
                            desc_elem = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
                            if not desc_elem:
                                continue

                            links = desc_elem.query_selector_all('a')

                            for link in links:
                                pdf_url = link.get_attribute('href')
                                if pdf_url and pdf_url.endswith('.pdf'):
                                    # Преобразуем относительный URL в абсолютный
                                    if not pdf_url.startswith('http'):
                                        pdf_url = urljoin(self.BASE_URL, pdf_url)

                                    # Формируем путь для сохранения
                                    issuer_dir = os.path.join(self.output_dir, self._sanitize_filename(issuer_name))
                                    isin_dir = os.path.join(issuer_dir, isin)

                                    # Получаем имя файла из URL
                                    filename = os.path.basename(urlparse(pdf_url).path)
                                    save_path = os.path.join(isin_dir, filename)

                                    # Скачиваем файл
                                    self.download_file(pdf_url, save_path)

                            break

                    except Exception as e:
                        logger.warning(f"Ошибка при обработке поля: {e}")
                        continue

            except Exception as e:
                logger.error(f"Ошибка при обработке облигации {bond['url']}: {e}")
                continue

            time.sleep(1)

    def get_rf_issuers(self) -> List[Dict]:
        """
        Получение списка РФ компаний (эмитентов)

        Returns:
            Список словарей с информацией об эмитентах
        """
        logger.info("Получение списка РФ компаний...")

        try:
            self.page.goto(self.ISSUERS_BASE_URL, wait_until='networkidle', timeout=30000)
            time.sleep(3)

            # Ждем загрузки ссылок на эмитентов
            self.page.wait_for_selector('a[href^="/issuers/"]', timeout=10000)

        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы эмитентов: {e}")
            return []

        issuers = []

        try:
            # Ищем ссылки на страницы эмитентов
            issuer_links = self.page.query_selector_all('a[href^="/issuers/"]')

            seen_links = set()

            for link in issuer_links:
                href = link.get_attribute('href')
                if href and '/issuers/' in href and href not in seen_links:
                    seen_links.add(href)

                    # Извлекаем ОГРН из URL
                    ogrn = href.split('/issuers/')[-1].strip('/')

                    if ogrn and ogrn.isdigit():
                        full_url = urljoin(self.ISSUERS_BASE_URL, href)
                        issuers.append({
                            'url': full_url,
                            'ogrn': ogrn
                        })

            logger.info(f"Найдено РФ эмитентов: {len(issuers)}")

        except Exception as e:
            logger.error(f"Ошибка при получении списка РФ эмитентов: {e}")

        return issuers

    def download_rf_prospectuses(self, issuers: List[Dict]):
        """
        Скачивание проспектов для РФ компаний

        Args:
            issuers: Список эмитентов
        """
        logger.info("Скачивание проспектов для РФ компаний...")

        for i, issuer in enumerate(issuers, 1):
            logger.info(f"Обработка эмитента {i}/{len(issuers)}: {issuer['ogrn']}")

            try:
                self.page.goto(issuer['url'], wait_until='networkidle', timeout=30000)
                time.sleep(3)

                # Получаем название эмитента
                try:
                    issuer_name_elem = self.page.query_selector('h1, .title, .issuer-name')
                    issuer_name = issuer_name_elem.inner_text().strip() if issuer_name_elem else issuer['ogrn']
                except Exception:
                    issuer_name = issuer['ogrn']

                # Ищем раздел с облигациями
                try:
                    # Пробуем найти и кликнуть на раздел "Ценные бумаги" (это div, не a)
                    securities_link = self.page.query_selector('div.t_level:has-text("Ценные бумаги"), li:has-text("Ценные бумаги")')
                    if securities_link:
                        securities_link.click()
                        logger.info(f"Кликнули на 'Ценные бумаги' для {issuer_name}")
                        time.sleep(2)

                        # Теперь кликаем на подраздел "Облигации"
                        bonds_link = self.page.query_selector('li#mn52, li:has-text("Облигации")')
                        if bonds_link:
                            bonds_link.click()
                            logger.info("Кликнули на 'Облигации'")
                            time.sleep(2)
                        else:
                            logger.warning(f"Не найден подраздел 'Облигации' для {issuer_name}")
                            continue
                    else:
                        logger.warning(f"Не найден раздел 'Ценные бумаги' для эмитента {issuer_name}")
                        continue
                except Exception as e:
                    logger.warning(f"Не удалось перейти к разделу ценных бумаг для {issuer_name}: {e}")
                    continue

                # Кликаем "Показать аннулированные" если есть
                try:
                    show_cancelled_btn = self.page.query_selector('input[value="Показать аннулированные"], button:has-text("Показать аннулированные")')
                    if show_cancelled_btn:
                        show_cancelled_btn.click()
                        logger.info("Кликнули 'Показать аннулированные'")
                        time.sleep(1)
                except Exception:
                    pass

                # Получаем список облигаций из таблицы
                # Ищем ссылки на "Государственный регистрационный номер"
                try:
                    # Подождем загрузки таблицы
                    time.sleep(2)

                    # Ищем все td с регистрационными номерами (они имеют класс ahref и onclick)
                    # По HTML: <td class="ahref" onclick=" ShowAction('...','alrs',event) ">4B02-03-40046-N-001P</td>
                    reg_number_cells = self.page.query_selector_all('td.ahref[onclick*="ShowAction"]')

                    logger.info(f"Найдено облигаций для {issuer_name}: {len(reg_number_cells)}")

                    for bond_idx, reg_cell in enumerate(reg_number_cells[:10]):  # Ограничим 10 для теста
                        try:
                            # Получаем текст ячейки (это и есть регистрационный номер)
                            reg_number = reg_cell.inner_text().strip()
                            logger.info(f"Обработка облигации: {reg_number}")

                            # Кликаем на ячейку чтобы открыть диалог с документами
                            reg_cell.click()
                            time.sleep(3)  # Ждем открытия диалога

                            # Ищем документы в открывшемся диалоге
                            # По HTML документы находятся в ссылках с href="/Documents/Index"
                            doc_links = self.page.query_selector_all('a[href*="/Documents/Index"]')

                            logger.info(f"Найдено документов для {reg_number}: {len(doc_links)}")

                            for link in doc_links:
                                try:
                                    link_text = link.inner_text().strip()
                                    pdf_url = link.get_attribute('href')

                                    # Фильтруем нужные типы документов согласно ТЗ
                                    doc_types_to_download = [
                                        'Решение о выпуске',
                                        'Проспект ценных бумаг',
                                        'Программа облигаций',
                                        'Условия размещения ценных бумаг'
                                    ]

                                    should_download = any(doc_type in link_text for doc_type in doc_types_to_download)

                                    if should_download and pdf_url:
                                        # Формируем полный URL
                                        if not pdf_url.startswith('http'):
                                            pdf_url = urljoin(self.ISSUERS_BASE_URL, pdf_url)

                                        logger.info(f"Скачивание: {link_text}")

                                        # Формируем путь для сохранения
                                        issuer_dir = os.path.join(self.output_dir, self._sanitize_filename(issuer_name))
                                        reg_dir = os.path.join(issuer_dir, self._sanitize_filename(reg_number))

                                        # Формируем имя файла из типа документа
                                        doc_type_filename = self._sanitize_filename(link_text)
                                        filename = f"{doc_type_filename}.zip"  # Обычно это ZIP файлы

                                        save_path = os.path.join(reg_dir, filename)

                                        # Скачиваем файл
                                        self.download_file(pdf_url, save_path)

                                except Exception as e:
                                    logger.warning(f"Ошибка при скачивании документа: {e}")
                                    continue

                            # Закрываем диалог после обработки документов
                            try:
                                # Пробуем закрыть диалог - ищем кнопку закрытия или нажимаем Escape
                                close_button = self.page.query_selector('.ui-dialog-titlebar-close, button:has-text("Закрыть")')
                                if close_button:
                                    close_button.click()
                                    time.sleep(1)
                                else:
                                    # Если кнопки нет, нажимаем Escape
                                    self.page.keyboard.press('Escape')
                                    time.sleep(1)
                            except Exception:
                                pass

                        except Exception as e:
                            logger.warning(f"Ошибка при обработке облигации {bond_idx}: {e}")
                            # Пробуем закрыть диалог в случае ошибки
                            try:
                                self.page.keyboard.press('Escape')
                                time.sleep(1)
                            except Exception:
                                pass
                            continue

                except Exception as e:
                    logger.warning(f"Ошибка при получении списка облигаций: {e}")
                    pass

            except Exception as e:
                logger.error(f"Ошибка при обработке эмитента {issuer['url']}: {e}")
                continue

            time.sleep(1)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Очистка имени файла от недопустимых символов

        Args:
            filename: Исходное имя файла

        Returns:
            Очищенное имя файла
        """
        # Заменяем недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Убираем множественные пробелы и подчеркивания
        filename = ' '.join(filename.split())
        filename = '_'.join(filter(None, filename.split('_')))

        return filename

    def parse_and_download_all(self, skip_foreign: bool = False, skip_rf: bool = False):
        """
        Основная функция для скачивания всех проспектов

        Args:
            skip_foreign: Пропустить иностранные облигации
            skip_rf: Пропустить РФ компании
        """
        self.setup_browser()

        try:
            # 1. Скачиваем проспекты для иностранных облигаций
            if not skip_foreign:
                logger.info("=" * 50)
                logger.info("ЭТАП 1: Иностранные облигации")
                logger.info("=" * 50)

                foreign_bonds = self.get_foreign_bonds()
                if foreign_bonds:
                    self.download_foreign_prospectuses(foreign_bonds)
            else:
                logger.info("Пропускаем этап иностранных облигаций")

            # 2. Скачиваем проспекты для РФ компаний
            if not skip_rf:
                logger.info("=" * 50)
                logger.info("ЭТАП 2: РФ компании")
                logger.info("=" * 50)

                rf_issuers = self.get_rf_issuers()
                if rf_issuers:
                    self.download_rf_prospectuses(rf_issuers)
            else:
                logger.info("Пропускаем этап РФ компаний")

            logger.info("=" * 50)
            logger.info("Скачивание проспектов завершено")
            logger.info(f"Всего скачано файлов: {len(self.downloaded_files)}")
            logger.info("=" * 50)

        finally:
            self.close_browser()


def main():
    """Основная функция запуска парсера проспектов"""
    logger.info("Запуск парсера проспектов SPBE")

    parser = SPBEProspectusParser(headless=True)

    try:
        parser.parse_and_download_all()
        logger.info("Парсинг успешно завершен")

    except Exception as e:
        logger.error(f"Ошибка при выполнении парсинга: {e}", exc_info=True)


if __name__ == "__main__":
    main()
