# backend/src/infrastructure/security/personal_data_cipher.py
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken


class PersonalDataCipher:
    def __init__(self, server_secret: str) -> None:
        if len(server_secret.encode()) < 32 or server_secret == "please-set-JWT_SECRET-in-env":
            raise ValueError("A configured server secret is required for reporting credentials")
        key = hmac.new(server_secret.encode(), b"auto-reports/personal-data/owner-grant/v1", hashlib.sha256).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, token: str) -> str:
        if not token:
            raise ValueError("Reporting credential is required")
        return self._fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except (InvalidToken, UnicodeError, ValueError):
            raise ValueError("Reporting credential cannot be decrypted") from None
