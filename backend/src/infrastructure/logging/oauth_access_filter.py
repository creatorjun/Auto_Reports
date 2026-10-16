# backend/src/infrastructure/logging/oauth_access_filter.py
import logging


class OAuthAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, target, protocol, status = record.args
            if isinstance(target, str) and target.split("?", 1)[0] == "/api/v1/auth/jira/callback":
                record.args = (client, method, target.split("?", 1)[0], protocol, status)
        return True
