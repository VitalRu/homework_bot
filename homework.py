import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='./homework.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(
        bot: telegram.bot.Bot, message: str
) -> telegram.message.Message:
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.debug(f'Отправка сообщения: {message}')
        return bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.error(f'Сообщение не отправлено: {error}')
        raise exceptions.SendMessageException(error)


def get_api_answer(timestamp: int) -> dict[str, list[dict[str, str]]]:
    """Делает запрос к API сервиса Практикум.Домашка."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException as error:
        message = f'Нет ответа от {ENDPOINT}. {error}'
        logger.error(message)
        raise exceptions.GetAPIAnswerException(message)
    if homework_statuses.status_code != HTTPStatus.OK:
        message = f'Код ответа API: {homework_statuses.status_code}'
        logger.error(message)
        raise exceptions.GetAPIAnswerException(message)
    try:
        return homework_statuses.json()
    except json.decoder.JSONDecodeError as error:
        message = f'Ошибка преобразования к формату json: {error}'
        logger.error(message)
        raise exceptions.GetAPIAnswerException(message)


def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        message = (f'Тип данных не соотвествует ожидаемому.'
                   f' Получен: {type(response)}')
        logger.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Ключ homeworks недоступен'
        logger.error(message)
        raise exceptions.CheckResponseException(message)
    homeworks_list = response['homeworks']
    if not isinstance(homeworks_list, list):
        message = (f'Ответ приходит не в виде списка. '
                   f'Получен: {type(homeworks_list)}')
        logger.error(message)
        raise TypeError(message)
    return homeworks_list


def parse_status(homework: dict) -> str:
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        message = 'Ключ homework_name недоступен'
        logger.error(message)
        raise KeyError(message)
    if 'status' not in homework:
        message = 'Ключ status недоступен'
        logger.error(message)
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message = (f'Передан неизвестный статус '
                   f'домашней работы "{homework_status}"')
        logger.error(message)
        logger.debug(homework_status)
        raise exceptions.ParseStatusException(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return (f'Изменился статус проверки работы '
            f'"{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения'
        logger.critical(message)
        raise exceptions.CheckTokensException(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status = ''
    error_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logger.info('Статус не обновлен')
            else:
                homework_status = parse_status(homework[0])
                if status == homework_status:
                    logger.debug(homework_status)
                else:
                    status = homework_status
                    send_message(bot, homework_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if error_message != str(error):
                error_message = str(error)
                try:
                    send_message(bot, message)
                except telegram.error.TelegramError as error:
                    logger.error(f'Не удалось отправить '
                                 f'сообщение об ошибке:{error}')
        finally:
            time.sleep(RETRY_PERIOD)
            timestamp = response['current_date']
            logger.debug(timestamp)


if __name__ == '__main__':
    main()
