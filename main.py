"""
SPBE Main Parser
Главный файл для запуска парсеров СПБ Биржи
"""

import logging
import argparse
from datetime import datetime
from spbe_parser import SPBEParser
from spbe_prospectus_parser import SPBEProspectusParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'spbe_parser_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_reference_data(headless: bool = True):
    """
    Запуск парсера референсных данных

    Args:
        headless: Запускать браузер в headless режиме
    """
    logger.info("=" * 70)
    logger.info("ЗАПУСК ПАРСЕРА РЕФЕРЕНСНЫХ ДАННЫХ")
    logger.info("=" * 70)

    parser = SPBEParser(headless=headless)

    try:
        # Парсим все облигации
        bonds_data = parser.parse_all_bonds()

        # Сохраняем в CSV
        parser.save_to_csv(bonds_data)

        logger.info("Парсинг референсных данных успешно завершен")
        return True

    except Exception as e:
        logger.error(f"Ошибка при выполнении парсинга референсных данных: {e}", exc_info=True)
        return False


def parse_prospectuses(headless: bool = True, output_dir: str = "Prospectuses"):
    """
    Запуск парсера проспектов

    Args:
        headless: Запускать браузер в headless режиме
        output_dir: Директория для сохранения проспектов
    """
    logger.info("=" * 70)
    logger.info("ЗАПУСК ПАРСЕРА ПРОСПЕКТОВ")
    logger.info("=" * 70)

    parser = SPBEProspectusParser(headless=headless, output_dir=output_dir)

    try:
        parser.parse_and_download_all()
        logger.info("Парсинг проспектов успешно завершен")
        return True

    except Exception as e:
        logger.error(f"Ошибка при выполнении парсинга проспектов: {e}", exc_info=True)
        return False


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description='Парсер данных с сайта СПБ Биржи',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Запуск обоих парсеров
  python main.py --all

  # Запуск только парсера референсных данных
  python main.py --reference-data

  # Запуск только парсера проспектов
  python main.py --prospectuses

  # Запуск с видимым браузером (для отладки)
  python main.py --all --no-headless

  # Указать директорию для сохранения проспектов
  python main.py --prospectuses --output-dir "My_Prospectuses"
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Запустить оба парсера (референсные данные и проспекты)'
    )

    parser.add_argument(
        '--reference-data',
        action='store_true',
        help='Запустить парсер референсных данных'
    )

    parser.add_argument(
        '--prospectuses',
        action='store_true',
        help='Запустить парсер проспектов'
    )

    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Запустить браузер в видимом режиме (для отладки)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='Prospectuses',
        help='Директория для сохранения проспектов (по умолчанию: Prospectuses)'
    )

    args = parser.parse_args()

    # Если не указан ни один флаг, показываем help
    if not (args.all or args.reference_data or args.prospectuses):
        parser.print_help()
        return

    headless = not args.no_headless

    logger.info("=" * 70)
    logger.info(f"SPBE PARSER - Запуск {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    results = []

    # Запуск парсера референсных данных
    if args.all or args.reference_data:
        success = parse_reference_data(headless=headless)
        results.append(('Референсные данные', success))

    # Запуск парсера проспектов
    if args.all or args.prospectuses:
        success = parse_prospectuses(headless=headless, output_dir=args.output_dir)
        results.append(('Проспекты', success))

    # Итоговый отчет
    logger.info("=" * 70)
    logger.info("ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 70)

    for task_name, success in results:
        status = "✓ УСПЕШНО" if success else "✗ ОШИБКА"
        logger.info(f"{task_name}: {status}")

    logger.info("=" * 70)
    logger.info(f"Завершено {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
