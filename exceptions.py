class BotException(Exception):
    """Базовый класс исключений."""

    pass


class CheckTokensException(BotException):
    """Исключение для функции check_tokens."""

    pass


class SendMessageException(BotException):
    """Исключение для функции send_message."""

    pass


class GetAPIAnswerException(BotException):
    """Исключение для функции get_api_answer."""

    pass


class CheckResponseException(BotException):
    """Исключение для функции check_response."""

    pass


class ParseStatusException(BotException):
    """Исключение для функции parse_status."""

    pass
