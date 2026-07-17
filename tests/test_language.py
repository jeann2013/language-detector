"""Tests for the raw language detector (no plugin/context involved)."""

from litellm_plugin_language_detector.detector import detect_language


def test_detects_spanish():
    result = detect_language("Hola, necesito ayuda con Python.")
    assert result["language"] == "es"
    assert result["detector"] == "lingua"
    assert result["confidence"] > 0.5


def test_detects_english():
    result = detect_language("Can you optimize this SQL query?")
    assert result["language"] == "en"
    assert result["confidence"] > 0.5


def test_detects_french():
    result = detect_language("Bonjour, pouvez-vous m'aider avec ce projet ?")
    assert result["language"] == "fr"
    assert result["confidence"] > 0.5


def test_detects_chinese():
    result = detect_language("你好,我需要帮助完成这个项目。")
    assert result["language"] == "zh"
    assert result["confidence"] > 0.5


def test_empty_text_is_unknown():
    result = detect_language("")
    assert result == {"language": "unknown", "confidence": 0.0, "detector": "lingua"}


def test_whitespace_only_is_unknown():
    result = detect_language("   \n\t  ")
    assert result["language"] == "unknown"
    assert result["confidence"] == 0.0


def test_emojis_only_is_unknown():
    result = detect_language("😀🎉🔥🚀😂")
    assert result["language"] == "unknown"
    assert result["confidence"] == 0.0


def test_code_snippet_never_raises():
    # Code isn't natural language -- the important part is that this never
    # raises and always returns a well-shaped dict, whatever the guess.
    result = detect_language(
        "def add(a, b):\n    return a + b\n\nprint(add(1, 2))"
    )
    assert set(result.keys()) == {"language", "confidence", "detector"}
    assert isinstance(result["confidence"], float)


def test_result_never_raises_on_garbage_input():
    result = detect_language("!!! ??? ... --- === 123456 000")
    assert set(result.keys()) == {"language", "confidence", "detector"}
