# backend/src/infrastructure/security/credential_encryptor.py
import os
from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptor:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, plaintext: str | None) -> str | None:
        if plaintext is None:
            return None
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str | None) -> str | None:
        if ciphertext is None:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            return None
