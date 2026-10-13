# backend/src/infrastructure/logging/audit_log_reader.py
import asyncio
import heapq
import json
import os
import re
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path

from src.application.ports.audit_log_reader_port import AuditLogReadError, AuditLogReaderPort
from src.domain.constants import KST
from src.domain.entities.audit_log import AuditLogEntry, AuditLogPage, AuditLogQuery
from src.infrastructure.logging.audit_format import safe_fields, safe_text

_FILE_NAME = re.compile(r"audit\.log(?:\.\d{4}-\d{2}-\d{2})?\Z")
_LINE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]? \[AUDIT\] (.+)$")
_MAX_LINE_BYTES = 262144


class FileAuditLogReader(AuditLogReaderPort):
    def __init__(self, log_dir: str = "logs") -> None:
        self._directory = Path(log_dir)

    async def read(self, query: AuditLogQuery) -> AuditLogPage:
        return await asyncio.to_thread(self._read, query)

    def _read(self, query: AuditLogQuery) -> AuditLogPage:
        for attempt in range(2):
            try:
                return self._scan(query)
            except FileNotFoundError:
                if attempt:
                    raise AuditLogReadError("감사 로그 파일이 교체되고 있습니다. 다시 조회해 주세요.") from None
            except OSError as error:
                raise AuditLogReadError("감사 로그 파일을 읽을 수 없습니다. 서버의 로그 저장 경로와 읽기 권한을 확인해 주세요.") from error
        raise AuditLogReadError("감사 로그 파일을 조회하지 못했습니다.")

    def _scan(self, query: AuditLogQuery) -> AuditLogPage:
        warnings: set[str] = set()
        events: set[str] = set()
        total = 0
        selected: list[tuple[datetime, str, int, AuditLogEntry]] = []
        try:
            paths = sorted((path for path in self._directory.iterdir() if _FILE_NAME.fullmatch(path.name)), key=lambda path: path.name, reverse=True)
        except FileNotFoundError:
            return AuditLogPage([], 0, query.limit, query.offset, warnings=["저장된 감사 로그가 없습니다."])
        if not paths:
            return AuditLogPage([], 0, query.limit, query.offset, warnings=["저장된 감사 로그가 없습니다."])
        with ExitStack() as stack:
            streams = []
            opened_paths = []
            identities: set[tuple[int, int]] = set()
            for path in paths:
                if path.is_symlink():
                    warnings.add("연결 파일인 감사 로그는 조회에서 제외했습니다.")
                    continue
                stream = stack.enter_context(path.open("rb"))
                stat = os.fstat(stream.fileno())
                identity = (stat.st_dev, stat.st_ino)
                if identity in identities:
                    continue
                identities.add(identity)
                streams.append(("~audit.log" if path.name == "audit.log" else path.name, stream, stat.st_size))
                opened_paths.append((path, identity))
            current_names = {path.name for path in self._directory.iterdir() if _FILE_NAME.fullmatch(path.name)}
            if current_names != {path.name for path in paths}:
                raise FileNotFoundError()
            for path, identity in opened_paths:
                current = path.stat()
                if (current.st_dev, current.st_ino) != identity:
                    raise FileNotFoundError()
            for name, stream, size in streams:
                remaining = size
                line_number = 0
                while remaining > 0:
                    raw = stream.readline(min(_MAX_LINE_BYTES + 1, remaining))
                    if not raw:
                        warnings.add("조회 중 일부 로그 파일이 변경되었습니다. 최신 상태를 다시 조회해 주세요.")
                        break
                    remaining -= len(raw)
                    line_number += 1
                    if len(raw) > _MAX_LINE_BYTES:
                        while not raw.endswith(b"\n") and remaining > 0:
                            raw = stream.readline(min(_MAX_LINE_BYTES + 1, remaining))
                            remaining -= len(raw)
                            if not raw:
                                break
                        warnings.add("길이 제한을 초과한 감사 로그가 있어 일부 기록을 제외했습니다.")
                        continue
                    if not raw.endswith(b"\n"):
                        warnings.add("기록 중인 마지막 줄은 다음 조회에 표시됩니다.")
                        continue
                    try:
                        parsed = self._parse(raw.decode("utf-8").rstrip("\r\n"))
                    except (UnicodeError, ValueError, TypeError):
                        parsed = None
                    if parsed is None:
                        warnings.add("형식을 확인할 수 없는 감사 로그가 있어 일부 기록을 제외했습니다.")
                        continue
                    timestamp, entry = parsed
                    if len(events) < 256:
                        events.add(entry.event)
                    elif entry.event not in events:
                        warnings.add("이벤트 종류가 많아 필터 목록에는 일부 종류만 표시합니다.")
                    if not self._matches(timestamp, entry, query):
                        continue
                    total += 1
                    if entry.username is None:
                        warnings.add("일부 기록에는 사용자 정보가 없어 확인 불가로 표시됩니다.")
                    item = (timestamp, name, line_number, entry)
                    if len(selected) < query.offset + query.limit:
                        heapq.heappush(selected, item)
                    elif item[:3] > selected[0][:3]:
                        heapq.heapreplace(selected, item)
        selected.sort(key=lambda item: item[:3], reverse=True)
        items = [item[3] for item in selected[query.offset:query.offset + query.limit]]
        return AuditLogPage(items, total, query.limit, query.offset, sorted(events), sorted(warnings))

    @staticmethod
    def _parse(line: str) -> tuple[datetime, AuditLogEntry] | None:
        match = _LINE.fullmatch(line)
        if match is None:
            return None
        legacy_time, body = match.groups()
        if body.startswith("{"):
            payload = json.loads(body)
            if not isinstance(payload, dict) or not isinstance(payload.get("event"), str) or not isinstance(payload.get("fields", {}), dict):
                return None
            timestamp = datetime.fromisoformat(payload.get("timestamp", legacy_time))
            event = safe_text(payload["event"], 100)
            details = safe_fields(payload.get("fields", {}))
        else:
            parts = body.split(" | ")
            timestamp = datetime.fromisoformat(legacy_time)
            event = safe_text(parts[0], 100)
            fields = {}
            for part in parts[1:]:
                key, separator, value = part.partition("=")
                if separator:
                    fields[key] = value
            details = safe_fields(fields)
        if not event:
            return None
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=KST)
        timestamp = timestamp.astimezone(KST)
        username = details.pop("username", None)
        ip = details.pop("ip", None)
        if username in ("", "None", "null"):
            username = None
        if ip in ("", "None", "null"):
            ip = None
        return timestamp, AuditLogEntry(timestamp.isoformat(), event, username, ip, details)

    @staticmethod
    def _matches(timestamp: datetime, entry: AuditLogEntry, query: AuditLogQuery) -> bool:
        if query.start_date and timestamp.date() < query.start_date:
            return False
        if query.end_date and timestamp.date() > query.end_date:
            return False
        if query.event and query.event.casefold() != entry.event.casefold():
            return False
        if query.username and query.username.casefold() not in (entry.username or "").casefold():
            return False
        if query.ip and query.ip.casefold() not in (entry.ip or "").casefold():
            return False
        searchable = " ".join((entry.event, entry.username or "", entry.ip or "", *(f"{key}={value}" for key, value in entry.details.items())))
        return not query.search or query.search.casefold() in searchable.casefold()
