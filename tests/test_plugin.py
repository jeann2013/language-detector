"""Tests for LanguageDetectorPlugin.run() -- the context in, context out contract."""

import pytest

from litellm_plugin_language_detector.plugin import (
    SIGNAL_NAMESPACE,
    LanguageDetectorPlugin,
    RoutingContext,
)


def _context(*messages):
    # raw_messages/candidate_models are required by the real RoutingContext
    # but irrelevant to this plugin, so the helper fills them with harmless
    # defaults.
    return RoutingContext(
        raw_messages=list(messages),
        structured_messages=list(messages),
        candidate_models=[],
    )


@pytest.mark.asyncio
async def test_publishes_signal_for_spanish_user_message():
    plugin = LanguageDetectorPlugin()
    context = _context({"role": "user", "content": "Hola, necesito ayuda con Python."})

    result = await plugin.run(context)

    signal = result.signals[SIGNAL_NAMESPACE]
    assert signal["language"] == "es"
    assert signal["detector"] == "lingua"


@pytest.mark.asyncio
async def test_publishes_signal_for_english_user_message():
    plugin = LanguageDetectorPlugin()
    context = _context({"role": "user", "content": "Can you optimize this SQL query?"})

    result = await plugin.run(context)

    assert result.signals[SIGNAL_NAMESPACE]["language"] == "en"


@pytest.mark.asyncio
async def test_ignores_non_user_roles():
    plugin = LanguageDetectorPlugin()
    context = _context(
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
        {"role": "tool", "content": "{\"result\": \"ok\"}"},
        {"role": "user", "content": "Can you optimize this SQL query?"},
    )

    result = await plugin.run(context)

    assert result.signals[SIGNAL_NAMESPACE]["language"] == "en"


@pytest.mark.asyncio
async def test_no_user_messages_is_unknown():
    plugin = LanguageDetectorPlugin()
    context = _context({"role": "assistant", "content": "Hello there."})

    result = await plugin.run(context)

    assert result.signals[SIGNAL_NAMESPACE] == {
        "language": "unknown",
        "confidence": 0.0,
        "detector": "lingua",
    }


@pytest.mark.asyncio
async def test_empty_messages_is_unknown():
    plugin = LanguageDetectorPlugin()
    context = _context()

    result = await plugin.run(context)

    assert result.signals[SIGNAL_NAMESPACE]["language"] == "unknown"


@pytest.mark.asyncio
async def test_never_raises_on_malformed_messages():
    # Real RoutingContext instances are validated by the Router, but a
    # plugin still shouldn't blow up if a message is missing keys or a list
    # ends up with a stray non-dict entry -- mutate past pydantic's
    # constructor validation to simulate that.
    plugin = LanguageDetectorPlugin()
    context = _context({"role": "user"})
    context.structured_messages.extend(["not-a-dict", None])

    result = await plugin.run(context)

    assert SIGNAL_NAMESPACE in result.signals


@pytest.mark.asyncio
async def test_does_not_touch_candidate_models():
    plugin = LanguageDetectorPlugin()
    context = RoutingContext(
        raw_messages=[{"role": "user", "content": "Hola"}],
        structured_messages=[{"role": "user", "content": "Hola"}],
        candidate_models=["gpt-4o", "claude-sonnet"],
    )

    result = await plugin.run(context)

    assert result.candidate_models == ["gpt-4o", "claude-sonnet"]


@pytest.mark.asyncio
async def test_supports_content_blocks():
    plugin = LanguageDetectorPlugin()
    context = _context(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hola, necesito ayuda con Python."},
                {"type": "image_url", "image_url": {"url": "https://example.com/x.png"}},
            ],
        }
    )

    result = await plugin.run(context)

    assert result.signals[SIGNAL_NAMESPACE]["language"] == "es"


@pytest.mark.asyncio
async def test_returns_same_context_instance():
    plugin = LanguageDetectorPlugin()
    context = _context({"role": "user", "content": "Hello"})

    result = await plugin.run(context)

    assert result is context
