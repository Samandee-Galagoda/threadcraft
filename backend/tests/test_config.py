"""Settings parsing.

These exist because a bad value here is uniquely destructive: Settings is
constructed at import time, so a parse failure kills the process before the app
starts. There is no request to return a 500 for and no log line explaining the
cause beyond a pydantic traceback — the only symptom is a crash-looping deploy.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**env):
    # _env_file=None so the developer's own .env can't influence the result.
    return Settings(_env_file=None, **env)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The spelling the docs ask for.
        ('["https://a.app","https://b.app"]', ["https://a.app", "https://b.app"]),
        # What someone actually pastes into a hosting dashboard's value box.
        # This used to raise SettingsError and crash-loop the deploy.
        ("https://threadcraft.vercel.app", ["https://threadcraft.vercel.app"]),
        # Comma-separated, the other obvious guess.
        ("https://a.app, https://b.app", ["https://a.app", "https://b.app"]),
        # A trailing slash never matches a browser Origin header, so it goes.
        ("https://a.app/", ["https://a.app"]),
        ("", []),
        (["https://a.app"], ["https://a.app"]),
    ],
)
def test_cors_origins_accepts_every_sane_spelling(raw, expected):
    assert _settings(cors_origins=raw).cors_origins == expected


def test_malformed_json_names_the_variable_and_the_expected_shape():
    """A parse failure is fatal at boot, so the message has to be enough to fix
    it from the deploy log alone."""
    with pytest.raises(ValidationError) as excinfo:
        _settings(cors_origins='["unclosed"')
    message = str(excinfo.value)
    assert "CORS_ORIGINS" in message
    assert "vercel.app" in message  # shows a correct example


def test_default_is_the_local_dev_origin():
    assert _settings().cors_origins == ["http://localhost:5173"]
