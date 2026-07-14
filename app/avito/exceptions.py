class AvitoAuthError(Exception):
    """Base exception for Avito authentication failures with safe messages only."""


class AvitoInvalidCredentialsError(AvitoAuthError):
    pass


class AvitoRateLimitError(AvitoAuthError):
    pass


class AvitoTemporaryError(AvitoAuthError):
    pass


class AvitoResponseValidationError(AvitoAuthError):
    pass
