import os
import logging
import time
import requests
import exception
import telegram


from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from http import HTTPStatus

load_dotenv()


def init_logger() -> logging.Logger:
    """Создания конифигурации логгера."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    file_handler = RotatingFileHandler(
        'homework.log',
        maxBytes=5000000,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = init_logger()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверка всех токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot: telegram.Bot, message: str) -> None:
    """Оповещает об изменение статуса проверки ДЗ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('сообщение отправлено')
    except Exception as error:
        logger.error(error)
        raise AssertionError(error)


def get_api_answer(timestamp: int) -> dict:
    """Получение ответа от API яндекс.практикум."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        logger.error(error)
        raise exception.UnavailableEndpointException(
            f'API не доступно : {error}'
        )
    if response.status_code != HTTPStatus.OK:
        raise exception.UnavailableEndpointException(
            'Указ не корректный URL.'
        )
    try:
        return response.json()
    except Exception as error:
        logger.error(error)
        raise exception.UnavailableEndpointException(
            'Ответ содержит некорректный тип данных.'
        )


def check_response(response: dict) -> list:
    """Проверка типов данных."""
    if not isinstance(response, dict):
        logger.error(
            'Неверный тип данных от API или некорректное форматирование.'
            f'Полученный тип данных {type(response)}'
        )
        raise TypeError(
            f'Получен не ожидаемый тип данных: {type(response)}'
        )
    if 'homeworks' not in response:
        logger.error('Отсутствует главный ключ!')
        raise KeyError('Отсутствует главный ключ!')
    key_list = response['homeworks']
    if not isinstance(key_list, list):
        logger.error('Полученные данные не являются списком.')
        raise TypeError(
            f'Получен не ожидаемый тип данных: {type(response)}'
        )
    if len(key_list) == 0:
        logger.info('Обновлений нет.')
        raise IndexError('отсутствует индекс')
    return key_list


def parse_status(homework: list) -> str:
    """Проверка статуса домашней работы."""
    keys = ('homework_name', 'status')
    for key in keys:
        if key not in homework:
            logger.error(f'Отсутствует ключ: {key}')
            raise KeyError(f'Отсутствует ключ: {key}')
    homework_name = homework['homework_name']
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    logger.error(f'передан неверный ключ {status}.')
    raise KeyError('Передан неверный ключ для значеи статуса.')


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует необходимый(e) токен(ы)!')
        raise exception.MissingTokenException(
            'Отсутствует необходимый(e) токен(ы)!'
        )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            list_response = check_response(response)
            hw_status = parse_status(list_response[0])
            if status == hw_status:
                logger.info(hw_status)
            status = hw_status
            send_message(bot, hw_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
