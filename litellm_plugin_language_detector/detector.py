"""Thin wrapper around ``lingua`` that turns free text into a signal dict.

Kept isolated from ``plugin.py`` so the detection backend can be swapped
(or the supported language list extended) without touching the plugin logic.
"""

from __future__ import annotations

from typing import Dict, Optional

from lingua import Language, LanguageDetector, LanguageDetectorBuilder

DETECTOR_NAME = "lingua"

UNKNOWN_RESULT: Dict[str, object] = {
    "language": "unknown",
    "confidence": 0.0,
    "detector": DETECTOR_NAME,
}

# ISO-639-1 codes for the languages supported in v1. Keep this list small on
# purpose: precision drops as more (similar) languages compete for the same
# text. Extend it only if a real need shows up.
_SUPPORTED_LANGUAGES = {
    Language.ENGLISH: "en",
    Language.SPANISH: "es",
    Language.FRENCH: "fr",
    Language.GERMAN: "de",
    Language.PORTUGUESE: "pt",
    Language.ITALIAN: "it",
    Language.DUTCH: "nl",
    Language.JAPANESE: "ja",
    Language.CHINESE: "zh",
    Language.KOREAN: "ko",
}

_detector: Optional[LanguageDetector] = None


def _get_detector() -> LanguageDetector:
    """Lazily build the singleton lingua detector.

    Building it loads language models, so it only happens once, on first
    use, instead of at import time.
    """
    global _detector
    if _detector is None:
        _detector = LanguageDetectorBuilder.from_languages(
            *_SUPPORTED_LANGUAGES.keys()
        ).build()
    return _detector


def detect_language(text: str) -> Dict[str, object]:
    """Detect the language of ``text``.

    Always returns a dict shaped like::

        {"language": "es", "confidence": 0.98, "detector": "lingua"}

    Falls back to the ``unknown`` result (never raises) when the text is
    empty, too short, or lingua can't make a confident call.
    """
    if not text or not text.strip():
        return dict(UNKNOWN_RESULT)

    try:
        detector = _get_detector()
        confidence_values = detector.compute_language_confidence_values(text)
    except Exception:
        return dict(UNKNOWN_RESULT)

    if not confidence_values:
        return dict(UNKNOWN_RESULT)

    top = confidence_values[0]
    language_code = _SUPPORTED_LANGUAGES.get(top.language)
    if language_code is None or top.value == 0.0:
        return dict(UNKNOWN_RESULT)

    return {
        "language": language_code,
        "confidence": round(top.value, 4),
        "detector": DETECTOR_NAME,
    }
