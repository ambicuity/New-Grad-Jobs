#!/usr/bin/env python3
"""Unit tests for Workday API URL construction helper."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from update_jobs import build_workday_api_url  # noqa: E402


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
