import pytest
from agnostic_llm.voice import VoiceEngine


def test_clean_text_for_speech():
    engine = VoiceEngine()
    raw = """
    # Welcome to Agnostic AI!
    Here is a `code snippet` and a [link](https://apple.com).
    ```python
    print("code block")
    ```
    - Bullet one
    - Bullet two
    **Bold emphasis**
    """
    clean = engine.clean_text_for_speech(raw)
    assert "code block" not in clean
    assert "https://apple.com" not in clean
    assert "Welcome to Agnostic AI!" in clean
    assert "Bullet one" in clean
    assert "Bold emphasis" in clean


def test_employee_voice_resolution():
    engine = VoiceEngine()
    assert engine.get_voice_for_employee("alex") in ["Samantha", "Daniel", "Karen", "Alex", "Fred"]
    assert engine.get_voice_for_employee("morgan") in ["Daniel", "Samantha", "Karen", "Alex", "Fred"]
    assert engine.get_voice_for_employee("taylor") in ["Karen", "Samantha", "Daniel", "Alex", "Fred"]
    assert engine.get_voice_for_employee("elena") in ["Moira", "Samantha", "Daniel", "Karen", "Alex", "Fred"]

