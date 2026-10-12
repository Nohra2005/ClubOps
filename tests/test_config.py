"""Central configuration: safe defaults, environment beats .env, the key stays secret."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from clubops.config import ModelMode, load_settings


def test_defaults_never_call_the_network(tmp_path: Path) -> None:
    settings = load_settings(env={}, dotenv=tmp_path / "missing.env")
    assert settings.mode is ModelMode.REPLAY
    assert settings.calls_network is False
    assert settings.api_key is None
    assert settings.budget_usd_per_packet == Decimal("0.50")


def test_environment_overrides_dotenv_and_key_is_secret(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "# comment\nCLUBOPS_MODEL=from-dotenv\nCLUBOPS_API_KEY='sk-test'\n"
        "CLUBOPS_BASE_URL=https://example.test/v1/\nnot a pair\n"
    )
    settings = load_settings(env={"CLUBOPS_MODEL": "from-env", "CLUBOPS_MODEL_MODE": "record"}, dotenv=dotenv)
    assert settings.model == "from-env"
    assert settings.base_url == "https://example.test/v1"
    assert settings.mode is ModelMode.RECORD and settings.calls_network
    assert settings.api_key is not None and settings.api_key.get_secret_value() == "sk-test"
    assert "sk-test" not in repr(settings)
