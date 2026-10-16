# backend/src/infrastructure/logging/oauth_access_filter.py
import logging


class OAuthAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, target, protocol, status = record.args
            if isinstance(target, str):
                route = target.split("?", 1)[0]
                if route == "/api" or route.startswith("/api/"):
                    record.args = (client, method, route, protocol, status)
        return True
