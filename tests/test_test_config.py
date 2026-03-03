from pathlib import Path

from test_config import validate_config


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_validate_config_success(tmp_path, capsys):
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

    code = validate_config(str(tmp_path / "config.yml"))

    out = capsys.readouterr().out
    assert code == 1  # under 10k still intentional warning path
    assert "YAML loaded successfully" in out
    assert "TOTAL: 5 companies" in out
    assert "WARNING" in out


def test_validate_config_file_not_found(tmp_path, capsys):
    code = validate_config(str(tmp_path / "missing.yml"))
    out = capsys.readouterr().out

    assert code == 1
    assert "Config file not found" in out


def test_validate_config_invalid_yaml(tmp_path, capsys):
    bad = tmp_path / "bad.yml"
    _write(bad, "apis: [\n")

    code = validate_config(str(bad))
    out = capsys.readouterr().out

    assert code == 1
    assert "Invalid YAML" in out


def test_validate_config_missing_required_key(tmp_path, capsys):
    bad = tmp_path / "bad.yml"
    _write(
        bad,
        """
apis:
  greenhouse:
    companies: [a]
""",
    )

    code = validate_config(str(bad))
    out = capsys.readouterr().out

    assert code == 1
    assert "Missing required config key" in out


def test_validate_config_empty_file(tmp_path, capsys):
    bad = tmp_path / "bad.yml"
    _write(bad, "")

    code = validate_config(str(bad))
    out = capsys.readouterr().out

    assert code == 1
    assert "Invalid config structure" in out
