"""Reference implementation of a LiteLLM Routing Plugin.

``LanguageDetectorPlugin`` looks at the latest user message, detects its
language, and publishes the result under
``context.signals["language-detector"]``. That's it.

It does not:

* narrow or otherwise touch ``context.candidate_models``
* mutate ``context.raw_messages``, ``context.structured_messages``, or
  ``context.metadata`` -- routing plugins only get to read those
* talk to the Router, a model, or the network
* raise exceptions back to the caller

Anything that is not detecting a language and publishing a signal belongs
in a different plugin.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

from .detector import UNKNOWN_RESULT, detect_language

try:
    # Real contract, available from litellm>=1.92 (Routing Plugins).
    from litellm.types.router import RoutingContext
except ImportError:  # pragma: no cover - exercised when litellm lacks the feature
    from pydantic import BaseModel, Field

    class RoutingContext(BaseModel):  # type: ignore[no-redef]
        """Local stand-in matching litellm's ``RoutingContext`` shape.

        Used only when the installed litellm doesn't ship Routing Plugins
        yet (pre-1.92), so this plugin can still be imported, tested, and
        run standalone. Any object exposing these five attributes works.
        """

        raw_messages: List[Dict[str, Any]] = Field(default_factory=list)
        structured_messages: List[Dict[str, Any]] = Field(default_factory=list)
        candidate_models: List[str] = Field(default_factory=list)
        metadata: Dict[str, Any] = Field(default_factory=dict)
        signals: Dict[str, Any] = Field(default_factory=dict)


SIGNAL_NAMESPACE = "language-detector"

# Roles whose content we actually analyze. Everything else (assistant, tool,
# system, ...) is ignored -- we only care about what the user wrote.
_ANALYZED_ROLE = "user"


def _message_text(content: Union[str, List[Dict[str, Any]], None]) -> str:
    """Flatten OpenAI-style message content into plain text.

    ``content`` is either a plain string, or a list of content blocks
    (``{"type": "text", "text": "..."}``, images, etc). Non-text blocks are
    ignored -- we only detect language from text.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return " ".join(part for part in parts if part)
    return ""


def _extract_user_text(structured_messages: List[Dict[str, Any]]) -> str:
    """Join the text of every ``user`` message, most recent last.

    Reads ``structured_messages`` (the provider-agnostic OpenAI chat shape)
    rather than ``raw_messages``, since we don't want to special-case every
    wire format (``/chat/completions``, ``/v1/messages``, Responses API).
    """
    texts = [
        _message_text(message.get("content"))
        for message in structured_messages
        if isinstance(message, dict) and message.get("role") == _ANALYZED_ROLE
    ]
    return " ".join(text for text in texts if text).strip()


class LanguageDetectorPlugin:
    """Detects the user's language and publishes it as a signal."""

    async def run(self, context: RoutingContext) -> RoutingContext:
        try:
            user_text = _extract_user_text(context.structured_messages)
            result = detect_language(user_text)
        except Exception:
            result = dict(UNKNOWN_RESULT)

        context.signals[SIGNAL_NAMESPACE] = result
        return context


# Ready-made singleton, handy for dotted-path plugin refs in proxy YAML
# (e.g. `litellm_plugin_language_detector.plugin.language_detector_plugin`).
language_detector_plugin = LanguageDetectorPlugin()
