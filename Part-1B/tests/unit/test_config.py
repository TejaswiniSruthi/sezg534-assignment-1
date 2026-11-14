"""Configuration and secrets (Constitution VI)."""

import pytest

from reminder_agent.config import load_settings, read_env_file
from reminder_agent.llm import ServiceError

SECRET = "test-key-not-real-123"


def test_env_file_parsing(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n\nGEMINI_API_KEY = \"quoted value\"\nGEMINI_MODEL='gemini-x-flash'\n"
        "PLAIN=a=b\nnot a pair\n",
        encoding="utf-8",
    )
    assert read_env_file(path) == {
        "GEMINI_API_KEY": "quoted value",
        "GEMINI_MODEL": "gemini-x-flash",
        "PLAIN": "a=b",
    }


def test_key_is_read_from_env_file_in_a_parent_folder(tmp_path):
    (tmp_path / ".env").write_text(f"GEMINI_API_KEY={SECRET}\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    settings = load_settings({}, nested)
    assert settings.api_key == SECRET
    assert settings.model is None
    assert settings.temperature == 0.0


def test_environment_wins_over_env_file(tmp_path):
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=from-file\nGEMINI_MODEL=file-model\n", encoding="utf-8"
    )
    environ = {"GEMINI_API_KEY": SECRET, "GEMINI_TEMPERATURE": "0.4"}
    settings = load_settings(environ, tmp_path)
    assert settings.api_key == SECRET
    assert settings.model == "file-model"
    assert settings.temperature == 0.4


@pytest.mark.parametrize("environ", [{}, {"GEMINI_API_KEY": ""}, {"GEMINI_API_KEY": "   "}])
def test_missing_key_is_a_service_error(tmp_path, environ):
    with pytest.raises(ServiceError) as caught:
        load_settings(environ, tmp_path)
    assert "GEMINI_API_KEY" in str(caught.value)


def test_bad_temperature_is_a_service_error(tmp_path):
    with pytest.raises(ServiceError):
        load_settings({"GEMINI_API_KEY": SECRET, "GEMINI_TEMPERATURE": "warm"}, tmp_path)


def test_settings_never_show_the_key(tmp_path):
    settings = load_settings({"GEMINI_API_KEY": SECRET}, tmp_path)
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
