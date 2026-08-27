from app.core.settings import settings


def test_settings_loaded() -> None:
    assert settings.app_name == "ResearchMind"
    assert settings.environment in ("development", "production", "test")
    assert settings.database_url != ""
    assert settings.valkey_url != ""
    assert settings.qdrant_url != ""


def test_eval_dashboard_admin_email_set_is_empty_by_default() -> None:
    """E7: no one has dashboard access until explicitly configured."""

    original = settings.eval_dashboard_admin_emails
    try:
        settings.eval_dashboard_admin_emails = ""
        assert settings.eval_dashboard_admin_email_set() == set()
    finally:
        settings.eval_dashboard_admin_emails = original


def test_eval_dashboard_admin_email_set_parses_comma_separated_emails() -> None:
    original = settings.eval_dashboard_admin_emails
    try:
        settings.eval_dashboard_admin_emails = "Alice@Example.com, bob@example.com ,"
        assert settings.eval_dashboard_admin_email_set() == {
            "alice@example.com",
            "bob@example.com",
        }
    finally:
        settings.eval_dashboard_admin_emails = original


def test_is_eval_dashboard_admin_matches_case_insensitively() -> None:
    original = settings.eval_dashboard_admin_emails
    try:
        settings.eval_dashboard_admin_emails = "alice@example.com"
        assert settings.is_eval_dashboard_admin("Alice@Example.com") is True
        assert settings.is_eval_dashboard_admin("bob@example.com") is False
    finally:
        settings.eval_dashboard_admin_emails = original
