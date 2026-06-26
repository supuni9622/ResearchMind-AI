from app.core.settings import settings


def test_settings_loaded() -> None:
    assert settings.app_name == "ResearchMind"
    assert settings.environment in ("development", "production")
    assert settings.database_url != ""
    assert settings.valkey_url != ""
    assert settings.qdrant_url != ""
