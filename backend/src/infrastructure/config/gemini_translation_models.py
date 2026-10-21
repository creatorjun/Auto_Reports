# backend/src/infrastructure/config/gemini_translation_models.py
from typing import Literal, get_args


SecurityNewsTranslationModel = Literal["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
DEFAULT_SECURITY_NEWS_TRANSLATION_MODEL: SecurityNewsTranslationModel = "gemini-3.5-flash-lite"
FREE_TIER_NEWS_TRANSLATION_MODELS = frozenset(get_args(SecurityNewsTranslationModel))
