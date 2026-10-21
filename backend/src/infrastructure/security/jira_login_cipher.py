# backend/src/infrastructure/security/jira_login_cipher.py
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken


class JiraLoginCipher:
    def __init__(self, server_secret: str) -> None:
        if len(server_secret.encode()) < 32 or server_secret == "please-set-JWT_SECRET-in-env":
            raise ValueError("A configured server secret is required for Jira login credentials")
        key = hmac.new(server_secret.encode(), b"auto-reports/jira-login/user-grant/v1", hashlib.sha256).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, token: str) -> str:
        if not isinstance(token, str) or not token or len(token) > 32768:
            raise ValueError("Invalid Jira login credential")
        return self._fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except (InvalidToken, UnicodeError, ValueError):
            raise ValueError("Jira login credential cannot be decrypted") from None
