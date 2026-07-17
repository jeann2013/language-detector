"""Language Detector Plugin -- reference LiteLLM Routing Plugin.

Detects the language of the user's message and publishes it to
``context.signals["language-detector"]``. Nothing else.
"""

from .detector import detect_language
from .plugin import LanguageDetectorPlugin, RoutingContext, language_detector_plugin

__all__ = [
    "LanguageDetectorPlugin",
    "RoutingContext",
    "detect_language",
    "language_detector_plugin",
]

__version__ = "1.0.0"
