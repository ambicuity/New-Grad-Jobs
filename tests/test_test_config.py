from pathlib import Path

from test_config import MIN_EXPECTED_COMPANIES, validate_config


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_validate_config_warning_path(tmp_path, caplog) -> None:
    _write(
        tmp_path / "config.yml",
        """
apis:
  greenhouse:
    companies: [a, b, c]
  lever:
    companies: [d]
  workday:
    companies: [e]
""",
    )

    caplog.set_level("INFO")
    code = validate_config(str(tmp_path / "config.yml"))

    logs = caplog.text
    assert code == 1
    assert "YAML loaded successfully" in logs
    assert "TOTAL: 5 companies" in logs
    assert "WARNING" in logs


def test_validate_config_threshold_success(tmp_path, caplog) -> None:
    companies = ", ".join(f"c{i}" for i in range(MIN_EXPECTED_COMPANIES))
    _write(
        tmp_path / "config.yml",
        f"""
apis:
  greenhouse:
    companies: [{companies}]
  lever:
    companies: []
  workday:
    companies: []
""",
    )

    caplog.set_level("INFO")
    code = validate_config(str(tmp_path / "config.yml"))

    logs = caplog.text
    assert code == 0
    assert f"TOTAL: {MIN_EXPECTED_COMPANIES} companies" in logs
    assert "WARNING" not in logs


def test_validate_config_file_not_found(tmp_path, caplog) -> None:
    caplog.set_level("INFO")
    code = validate_config(str(tmp_path / "missing.yml"))

    assert code == 1
    assert "Config file not found" in caplog.text


def test_validate_config_invalid_yaml(tmp_path, caplog) -> None:
    bad = tmp_path / "bad.yml"
    _write(bad, "apis: [\n")

    caplog.set_level("INFO")
    code = validate_config(str(bad))

    assert code == 1
    assert "Invalid YAML" in caplog.text


def test_validate_config_missing_required_key(tmp_path, caplog) -> None:
    bad = tmp_path / "bad.yml"
    _write(
        bad,
        """
apis:
  greenhouse:
    companies: [a]
""",
    )

    caplog.set_level("INFO")
    code = validate_config(str(bad))

    assert code == 1
    assert "Missing required config key" in caplog.text


def test_validate_config_empty_file(tmp_path, caplog) -> None:
    bad = tmp_path / "bad.yml"
    _write(bad, "")

    caplog.set_level("INFO")
    code = validate_config(str(bad))

    assert code == 1
    assert "Invalid config structure" in caplog.text
