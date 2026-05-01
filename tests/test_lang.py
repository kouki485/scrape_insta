from src.lang import is_japanese


def test_returns_true_for_japanese_text():
    assert is_japanese("浅草寺で雷門を見てきました") is True


def test_returns_true_for_japanese_with_emoji():
    assert is_japanese("今日は浅草に来てるよ〜🎌") is True


def test_returns_false_for_english_text():
    assert is_japanese("Just visited Sensoji Temple, amazing place!") is False


def test_returns_false_for_korean_text():
    assert is_japanese("아사쿠사 너무 좋아요") is False


def test_returns_false_for_chinese_text():
    assert is_japanese("今天去了浅草寺非常美丽") is False


def test_returns_false_for_thai_text():
    assert is_japanese("วันนี้ไปอาซากุสะมา") is False


def test_returns_false_for_empty_string():
    assert is_japanese("") is False


def test_returns_false_for_only_whitespace():
    assert is_japanese("   ") is False


def test_returns_false_for_only_emoji_or_symbols():
    assert is_japanese("🎌📸✨") is False


def test_returns_false_for_url_only():
    assert is_japanese("https://example.com/asakusa") is False
