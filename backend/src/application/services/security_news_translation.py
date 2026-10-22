# backend/src/application/services/security_news_translation.py
import asyncio
import hashlib
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timezone

from src.application.ports.security_news_translation_port import (
    NewsTranslationCachePort,
    NewsTranslationPort,
    NewsTranslationProviderError,
)
from src.domain.entities.security_news import SecurityNewsItem
from src.domain.entities.security_news_translation import NewsTranslation, NewsTranslationInput, NewsTranslationState


logger = logging.getLogger(__name__)
HANGUL = re.compile(r"[가-힣]")
CVE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
NUMBER = re.compile(r"\d+(?:\.\d+)*")


def translation_key(title: str, summary: str) -> str:
    encoded = json.dumps(["ko", title, summary], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def needs_translation(item: SecurityNewsItem) -> bool:
    if item.kind == "cve" or item.source_id == "kisa":
        return False
    prose = CVE.sub("", f"{item.title} {item.summary}")
    korean = len(HANGUL.findall(prose))
    english = len(re.findall(r"[A-Za-z]{3,}", prose))
    return bool(english) and not (korean >= 8 and korean >= english * 3)


def valid_translation(original: NewsTranslationInput, translated: NewsTranslation) -> bool:
    if original.key != translated.key or not translated.title_ko.strip():
        return False
    if len(translated.title_ko) > 1000 or len(translated.summary_ko) > 6000:
        return False
    if bool(original.summary.strip()) != bool(translated.summary_ko.strip()):
        return False
    if original.summary.strip() and re.search(r"[A-Za-z]{3,}", CVE.sub("", original.summary)):
        if not HANGUL.search(translated.title_ko + translated.summary_ko):
            return False
    for source, target in ((original.title, translated.title_ko), (original.summary, translated.summary_ko)):
        if set(value.upper() for value in CVE.findall(source)) != set(value.upper() for value in CVE.findall(target)):
            return False
        source_numbers = set(NUMBER.findall(re.sub(r"(?<=\d),(?=\d)", "", source)))
        target_numbers = set(NUMBER.findall(re.sub(r"(?<=\d),(?=\d)", "", target)))
        if not source_numbers.issubset(target_numbers):
            return False
        if set(re.findall(r"\d+(?:\.\d+)+", source)) != set(re.findall(r"\d+(?:\.\d+)+", target)):
            return False
        if re.search(r"<\s*/?\s*[A-Za-z]", target):
            return False
        if len(re.findall(r"[A-Za-z]{3,}", CVE.sub("", source))) >= 3 and not HANGUL.search(target):
            return False
    return True


class SecurityNewsTranslationService:
    def __init__(
        self,
        translator: NewsTranslationPort,
        cache: NewsTranslationCachePort,
        *,
        daily_limit: int = 60,
        batch_size: int = 10,
        minimum_interval_seconds: float = 10,
        max_attempts: int = 3,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._translator = translator
        self._cache = cache
        self._daily_limit = daily_limit
        self._batch_size = batch_size
        self._minimum_interval = minimum_interval_seconds
        self._max_attempts = max_attempts
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sleep = sleep
        self._inputs: dict[str, NewsTranslationInput] = {}
        self._prepared: dict[tuple[str, str, str, str], tuple[str, NewsTranslationInput | None]] = {}
        self._translations: dict[str, NewsTranslation] = {}
        self._task: asyncio.Task[None] | None = None
        self._not_before: datetime | None = None
        self._message: str | None = None
        self._cache_failed = False
        self._exhausted_inputs: frozenset[str] | None = None
        self._closed = False

    def snapshot(
        self, items: tuple[SecurityNewsItem, ...], *, start: bool = True,
    ) -> tuple[tuple[SecurityNewsItem, ...], NewsTranslationState]:
        prepared = {}
        keyed_items = []
        inputs = {}
        for item in items:
            content = (item.kind, item.source_id, item.title, item.summary)
            entry = prepared.get(content) or self._prepared.get(content)
            if entry is None:
                key = translation_key(item.title, item.summary)
                value = NewsTranslationInput(key, item.title, item.summary) if needs_translation(item) else None
                entry = (key, value)
            prepared[content] = entry
            key, value = entry
            keyed_items.append((item, key))
            if value is not None:
                inputs[key] = value
        self._prepared = prepared
        if start:
            if inputs.keys() != self._inputs.keys():
                self._not_before = None
                self._exhausted_inputs = None
            self._inputs = inputs
        missing = set(inputs).difference(self._translations)
        running = self._task is not None and not self._task.done()
        if (
            start and missing and not running and not self._cache_failed and not self._closed
            and self._exhausted_inputs != frozenset(inputs)
            and (self._not_before is None or self._clock() >= self._not_before)
        ):
            self._task = asyncio.create_task(self._run(), name="security-news-translation")
            running = True
        translated_count = 0
        pending_count = 0
        rendered = []
        for item, key in keyed_items:
            if item.kind == "cve":
                rendered.append(replace(item, title_ko=None, summary_ko=None))
                continue
            translation = self._translations.get(key)
            if translation is not None:
                rendered.append(replace(item, title_ko=translation.title_ko, summary_ko=translation.summary_ko))
                translated_count += 1
            else:
                rendered.append(item)
                pending_count += int(key in inputs)
        return tuple(rendered), NewsTranslationState(
            enabled=True, translating=running and bool(inputs), translated_count=translated_count,
            pending_count=pending_count, message=self._message if inputs else None,
        )

    async def restore(self, items: tuple[SecurityNewsItem, ...]) -> None:
        keys = tuple({translation_key(item.title, item.summary) for item in items if needs_translation(item)})
        if not keys:
            return
        try:
            self._translations.update(await self._cache.read(keys))
        except Exception as error:
            logger.warning("Security news translation cache unavailable: %s", type(error).__name__)
            self._cache_failed = True
            self._message = "번역 저장소를 사용할 수 없어 새 번역을 중지했습니다. 저장된 번역과 원문을 표시합니다."

    async def _run(self) -> None:
        try:
            while not self._closed:
                input_signature = frozenset(self._inputs)
                self._translations.update(await self._cache.read(tuple(input_signature)))
                if input_signature != frozenset(self._inputs):
                    continue
                pending = tuple(value for key, value in self._inputs.items() if key not in self._translations)
                if not pending:
                    self._message = None
                    return
                reservation = await self._cache.reserve(
                    pending, now=self._clock(), daily_limit=self._daily_limit,
                    batch_size=self._batch_size, minimum_interval_seconds=self._minimum_interval,
                    max_attempts=self._max_attempts,
                )
                self._not_before = reservation.next_attempt_at
                self._message = reservation.message
                if not reservation.inputs:
                    if input_signature != frozenset(self._inputs):
                        continue
                    if reservation.next_attempt_at is None:
                        self._exhausted_inputs = input_signature
                    delay = (
                        (reservation.next_attempt_at - self._clock()).total_seconds()
                        if reservation.next_attempt_at is not None else None
                    )
                    if delay is not None and 0 < delay <= 60:
                        await self._sleep(delay)
                        continue
                    return
                active_inputs = tuple(value for value in reservation.inputs if value.key in self._inputs)
                if not active_inputs:
                    continue
                failure = None
                translations: tuple[NewsTranslation, ...] = ()
                try:
                    returned = await self._translator.translate(active_inputs)
                    originals = {value.key: value for value in active_inputs}
                    valid = {
                        value.key: value for value in returned
                        if value.key in originals and valid_translation(originals[value.key], value)
                    }
                    translations = tuple(valid.values())
                    if len(translations) != len(active_inputs):
                        failure = "invalid"
                except NewsTranslationProviderError as error:
                    failure = error.reason
                except Exception as error:
                    logger.warning("Security news translation failed: %s", type(error).__name__)
                    failure = "provider"
                save = asyncio.create_task(self._cache.complete(
                    active_inputs, translations, now=self._clock(), failure=failure,
                ))
                try:
                    await asyncio.shield(save)
                except asyncio.CancelledError:
                    await save
                    raise
                self._translations.update({value.key: value for value in translations})
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning("Security news translation cache unavailable: %s", type(error).__name__)
            self._cache_failed = True
            self._message = "번역 저장소를 사용할 수 없어 새 번역을 중지했습니다. 저장된 번역과 원문을 표시합니다."

    async def aclose(self) -> None:
        self._closed = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
