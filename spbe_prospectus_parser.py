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

        # Теперь парсим таблицу и фильтруем по колонке "Категория"
        # Читаем все строки таблицы и ищем "иностранного эмитента"
        try:
            from bs4 import BeautifulSoup

            page_html = self.page.content()
            soup = BeautifulSoup(page_html, 'html.parser')

            # Находим таблицу (пробуем разные классы)
            table = soup.find('table', class_='Table_display__szeQI')
            if not table:
                table = soup.find('table', class_='Table_table__dOaFP')
            if not table:
                table = soup.find('table')  # Любая таблица

            if not table:
                logger.warning("Таблица не найдена в HTML")
                return foreign_bonds
            else:
                logger.info(f"Таблица найдена с классом: {table.get('class')}")

            # Находим заголовки для определения индекса колонки
            thead = table.find('thead')
            headers = []
            if thead:
                for th in thead.find_all('th'):
                    headers.append(th.get_text(strip=True))

            logger.info(f"Найдено колонок в таблице: {len(headers)}")
            if headers:
                logger.info(f"Заголовки: {headers}")

            # Ищем индекс колонки с категорией
            # Может называться "Вид, категория (тип) ценной бумаги" или просто "Категория"
            category_idx = None
            for idx, header in enumerate(headers):
                if 'категория' in header.lower() or 'тип' in header.lower():
                    category_idx = idx
                    logger.info(f"Колонка категории найдена под индексом {idx}: '{header}'")
                    break

            if category_idx is None:
                logger.warning("Колонка с категорией не найдена")
                # Пробуем альтернативный метод - по всем ссылкам card_bond (иностранные)
                logger.info("Используем альтернативный метод: фильтруем по типу ссылки card_bond")
                bond_links = self.page.query_selector_all('a[href*="/listing/securities/card_bond/?issue="]')

                seen_links = set()
                for link in bond_links:
                    href = link.get_attribute('href')
                    if href and href not in seen_links:
                        seen_links.add(href)
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        issue_id = href.split('issue=')[-1] if 'issue=' in href else None
                        if issue_id:
                            # Извлекаем ISIN из текста ссылки
                            isin = link.inner_text().strip() if link.inner_text() else None

                            # issuer_name будет получен позже при заходе на детальную страницу
                            foreign_bonds.append({
                                'url': href,
                                'issue_id': issue_id,
                                'isin': isin,
                                'issuer_name': None  # Будет заполнено позже
                            })
                            logger.info(f"Найдена иностранная облигация: {isin}")

                logger.info(f"Найдено иностранных облигаций по ссылкам: {len(foreign_bonds)}")
                return foreign_bonds

            # Парсим строки таблицы
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                logger.info(f"Найдено строк в таблице: {len(rows)}")

                for row_idx, row in enumerate(rows):
                    cells = row.find_all('td')

                    if len(cells) <= category_idx:
                        logger.debug(f"Строка {row_idx}: недостаточно колонок ({len(cells)})")
                        continue

                    # Проверяем категорию
                    category_cell = cells[category_idx]
                    category_text = category_cell.get_text(strip=True)

                    logger.info(f"Строка {row_idx}: категория = '{category_text}'")

                    # Фильтруем только "иностранного эмитента"
                    if 'иностранного эмитента' in category_text.lower():
                        logger.info(f"Строка {row_idx}: найдена категория 'иностранного эмитента'")

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

        except Exception as e:
            logger.error(f"Ошибка при парсинге таблицы: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
                    # Пробуем найти и кликнуть на раздел "Ценные бумаги"
                    securities_link = self.page.query_selector('a:has-text("Ценные бумаги"), a:has-text("ценные бумаги")')
                    if securities_link:
                        securities_link.click()
                        time.sleep(2)
                    else:
                        logger.warning(f"Не найден раздел 'Ценные бумаги' для эмитента {issuer_name}")
                        continue
                except Exception:
                    logger.warning(f"Не удалось перейти к разделу ценных бумаг для {issuer_name}")
                    continue

                # Кликаем "Показать аннулированные" если есть
                try:
                    show_cancelled_btn = self.page.query_selector('button:has-text("Показать аннулированные"), button:has-text("показать аннулированные")')
                    if show_cancelled_btn:
                        show_cancelled_btn.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Получаем список облигаций
                try:
                    bond_rows = self.page.query_selector_all('tr, .bond-row, .security-row')
                except Exception:
                    bond_rows = []

                for bond_row in bond_rows:
                    try:
                        # Кликаем на строку с облигацией
                        bond_row.click()
                        time.sleep(1)

                        # Ищем ISIN
                        isin = None
                        try:
                            isin_elem = self.page.query_selector('td:has-text("ISIN") + td, div:has-text("ISIN") + div')
                            if isin_elem:
                                isin = isin_elem.inner_text().strip()
                        except Exception:
                            pass

                        if not isin:
                            try:
                                all_text = bond_row.inner_text()
                                if 'ISIN' in all_text:
                                    parts = all_text.split('ISIN')
                                    if len(parts) > 1:
                                        isin = parts[1].strip().split()[0]
                            except Exception:
                                pass

                        if not isin:
                            logger.warning("ISIN не найден для облигации")
                            continue

                        # Ищем все документы для этой облигации
                        doc_links = self.page.query_selector_all('a[href*=".pdf"], a[download]')

                        for link in doc_links:
                            pdf_url = link.get_attribute('href')
                            if pdf_url and '.pdf' in pdf_url.lower():
                                # Формируем полный URL если нужно
                                if not pdf_url.startswith('http'):
                                    pdf_url = urljoin(issuer['url'], pdf_url)

                                # Формируем путь для сохранения
                                issuer_dir = os.path.join(self.output_dir, self._sanitize_filename(issuer_name))
                                isin_dir = os.path.join(issuer_dir, isin)

                                # Получаем имя файла
                                filename = os.path.basename(urlparse(pdf_url).path)
                                if not filename or filename == '':
                                    filename = f"document_{i}.pdf"

                                save_path = os.path.join(isin_dir, filename)

                                # Скачиваем файл
                                self.download_file(pdf_url, save_path)

                    except Exception as e:
                        logger.warning(f"Ошибка при обработке облигации: {e}")
                        continue

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

    def parse_and_download_all(self):
        """Основная функция для скачивания всех проспектов"""
        self.setup_browser()

        try:
            # 1. Скачиваем проспекты для иностранных облигаций
            logger.info("=" * 50)
            logger.info("ЭТАП 1: Иностранные облигации")
            logger.info("=" * 50)

            foreign_bonds = self.get_foreign_bonds()
            if foreign_bonds:
                self.download_foreign_prospectuses(foreign_bonds)

            # 2. Скачиваем проспекты для РФ компаний
            logger.info("=" * 50)
            logger.info("ЭТАП 2: РФ компании")
            logger.info("=" * 50)

            rf_issuers = self.get_rf_issuers()
            if rf_issuers:
                self.download_rf_prospectuses(rf_issuers)

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
