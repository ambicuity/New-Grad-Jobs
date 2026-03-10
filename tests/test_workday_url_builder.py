#!/usr/bin/env python3
"""Unit tests for Workday API URL construction helper."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import build_workday_api_url, get_workday_csrf_token  # noqa: E402


def test_build_workday_api_url_uses_host_tenant_for_standard_urls():
    api_url = build_workday_api_url(
        "nvidia.wd5.myworkdayjobs.com",
        "/NVIDIA_External_Career_Site",
    )
    assert api_url == "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIA_External_Career_Site/jobs"


def test_build_workday_api_url_handles_locale_prefix_without_changing_tenant():
    api_url = build_workday_api_url(
        "microsoft.wd10.myworkdayjobs.com",
        "/en-US/Microsoft",
    )
    assert api_url == "https://microsoft.wd10.myworkdayjobs.com/wday/cxs/microsoft/Microsoft/jobs"


def test_build_workday_api_url_uses_path_tenant_for_wd_subdomain_hosts():
    api_url = build_workday_api_url(
        "wd5.myworkdayjobs.com",
        "/acme/Acme_External_Careers",
    )
    assert api_url == "https://wd5.myworkdayjobs.com/wday/cxs/acme/Acme_External_Careers/jobs"


def test_build_workday_api_url_uses_second_segment_for_locale_prefixed_wd_hosts():
    api_url = build_workday_api_url(
        "wd5.myworkdayjobs.com",
        "/en-US/acme/Acme_External_Careers",
    )
    assert api_url == "https://wd5.myworkdayjobs.com/wday/cxs/acme/Acme_External_Careers/jobs"


def test_build_workday_api_url_rejects_empty_site_path():
    with pytest.raises(ValueError, match="site_path"):
        build_workday_api_url("acme.wd5.myworkdayjobs.com", "/")


def test_build_workday_api_url_rejects_blank_host():
    with pytest.raises(ValueError, match="host"):
        build_workday_api_url("   ", "/Acme_External_Careers")


def test_build_workday_api_url_rejects_none_inputs():
    with pytest.raises(ValueError, match="host"):
        build_workday_api_url(None, "/Acme_External_Careers")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="site_path"):
        build_workday_api_url("acme.wd5.myworkdayjobs.com", None)  # type: ignore[arg-type]


def test_build_workday_api_url_supports_unicode_and_long_site_names():
    long_site_name = "S" * 512
    unicode_site_name = f"{long_site_name}_R&D_日本"
    api_url = build_workday_api_url("acme.wd5.myworkdayjobs.com", f"/{unicode_site_name}")
    assert api_url == f"https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/{unicode_site_name}/jobs"


# ---------------------------------------------------------------------------
# Tests for get_workday_csrf_token()
# ---------------------------------------------------------------------------

class TestGetWorkdayCsrfToken:
    """Unit tests for CSRF token acquisition from Workday careers homepage."""

    def _make_session(self, headers=None, cookies=None, raises=None):
        """Build a mock session whose .get() returns a response with the given headers/cookies."""
        mock_response = MagicMock()
        mock_response.headers = headers or {}
        mock_response.cookies = cookies or {}
        session = MagicMock()
        if raises:
            session.get.side_effect = raises
        else:
            session.get.return_value = mock_response
        return session

    def test_returns_token_from_response_header(self):
        session = self._make_session(headers={"X-Calypso-CSRF-Token": "abc123"})
        token = get_workday_csrf_token("boeing.wd1.myworkdayjobs.com", session)
        assert token == "abc123"
        session.get.assert_called_once_with(
            "https://boeing.wd1.myworkdayjobs.com/",
            timeout=5,
            allow_redirects=True,
        )

    def test_falls_back_to_cookie_when_header_absent(self):
        session = self._make_session(
            headers={},
            cookies={"CALYPSO_CSRF_TOKEN": "cookie_token_xyz"},
        )
        token = get_workday_csrf_token("raytheon.wd5.myworkdayjobs.com", session)
        assert token == "cookie_token_xyz"

    def test_returns_empty_string_when_neither_header_nor_cookie_present(self):
        session = self._make_session(headers={}, cookies={})
        token = get_workday_csrf_token("acme.wd1.myworkdayjobs.com", session)
        assert token == ""

    def test_graceful_degradation_on_network_error(self, capsys):
        session = self._make_session(raises=ConnectionError("network down"))
        token = get_workday_csrf_token("acme.wd1.myworkdayjobs.com", session)
        assert token == ""
        captured = capsys.readouterr()
        assert "Could not acquire Workday CSRF token" in captured.out

    def test_header_takes_precedence_over_cookie(self):
        session = self._make_session(
            headers={"X-Calypso-CSRF-Token": "from_header"},
            cookies={"CALYPSO_CSRF_TOKEN": "from_cookie"},
        )
        token = get_workday_csrf_token("acme.wd1.myworkdayjobs.com", session)
        assert token == "from_header"
