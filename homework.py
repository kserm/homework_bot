"""Bot to check Yandex Praktikum homework status."""

import os
import sys
import logging
import time
import telegram
import requests
import settings
from http import HTTPStatus
from dotenv import load_dotenv
from logging import StreamHandler

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)


def error_logging(message):
    """Log method for errors."""
    logger.error(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logger.error(error)


def send_message(bot, message):
    """Send message to telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logger.error(error)


def get_api_answer(current_timestamp):
    """Get request to API-service endpoint."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(settings.ENDPOINT,
                                         headers=settings.HEADERS,
                                         params=params)
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        elif homework_statuses.status_code == HTTPStatus.NOT_FOUND:
            error_logging(
                'Сбой в работе программы: '
                f'Эндпоинт {settings.ENDPOINT} недоступен. '
                f'Код ответа API: {homework_statuses.status_code}'
            )
        else:
            error_logging('Сбой при запросе к эндпоинту')
    except Exception as error:
        error_logging(error)
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError(f'Error {homework_statuses.status_code}')


def check_response(response):
    """Check if API response is correct."""
    if response == {}:
        error_logging('Ответ API содержит пустой словарь')
        raise IndexError('Ответ API содержит пустой словарь')
    elif type(response) == dict:
        if settings.HOMEWORKS_KEY in response:
            homeworks = response['homeworks']
            if isinstance(homeworks, list):
                return homeworks
            else:
                raise TypeError('Объект homeworks не является списком')
        else:
            error_logging(f'В ответе API отсутствует ключ {key}')
            raise KeyError(f'В ответе API отсутствует ключ {key}')
    else:
        error_logging('Ответ API не приведен к типам данных Python')
        raise TypeError('Ответ API не приведен к типам данных Python')


def parse_status(homework):
    """Parse homework status from response data."""
    if settings.HOMEWORK_NAME_KEY in homework:
        homework_name = homework[settings.HOMEWORK_NAME_KEY]
    else:
        error_logging(f'Отсутствует ключ {settings.HOMEWORK_NAME_KEY}')
        raise KeyError(f'Отсутствует ключ {settings.HOMEWORK_NAME_KEY}')
    if settings.HOMEWORK_STATUS_KEY in homework:
        homework_status = homework[settings.HOMEWORK_STATUS_KEY]
    else:
        error_logging(f'Отсутствует ключ {settings.HOMEWORK_STATUS_KEY}')
        raise KeyError(f'Отсутствует ключ {settings.HOMEWORK_STATUS_KEY}')
    if homework_status in settings.HOMEWORK_STATUSES:
        verdict = settings.HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        error_logging('Обнаружен недокументированный статус'
                      f'домашней работы {homework_status}')
        raise ValueError(f'Invalid status "{homework_status}"')


def check_tokens():
    """Check if all tokens are available."""
    if not PRACTICUM_TOKEN:
        logger.critical(
            "Отсутствует обязательная переменная окружения: 'PRACTICUM_TOKEN'")
        return False
    elif not TELEGRAM_TOKEN:
        logger.critical(
            "Отсутствует обязательная переменная окружения: 'TELEGRAM_TOKEN'")
        return False
    elif not TELEGRAM_CHAT_ID:
        logger.critical(
            "Отсутствует обязательная переменная окружения: 'TELEGRAM_CHAT_ID'"
        )
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_logging('Не пройдена проверка на наличие '
                      'обязательных переменных окружения')
    else:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                if homework:
                    hw_status = parse_status(homework[0])
                    if hw_status:
                        send_message(bot, hw_status)
                else:
                    logger.debug('В ответе отсутствует новый статус')
                current_timestamp = response['current_date']
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                error_logging(message)
            finally:
                time.sleep(settings.RETRY_TIME)


if __name__ == '__main__':
    main()
