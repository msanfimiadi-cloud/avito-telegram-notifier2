from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(ValueError):
    pass


class SecretCipher:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise EncryptionError("APP_ENCRYPTION_KEY must be a valid Fernet key") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, secret: str) -> str:
        if not secret:
            raise EncryptionError("Secret must not be empty")
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt(self, encrypted_secret: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_secret.encode()).decode()
        except InvalidToken as exc:
            raise EncryptionError("Unable to decrypt secret with configured key") from exc
