class MissingTokenException(Exception):
    """Исключение в случае отсутствия токена."""

    pass


class UnavailableEndpointException(Exception):
    """Исключение для недоступного или неверного API."""

    pass
