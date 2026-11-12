"""Packaging: psycopg ships as binary wheels, compiled is opt-in (issue #9)."""

import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads(
    (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
)


def _names(deps: list[str]) -> set[str]:
    return {d.split(">")[0].split("=")[0].split("<")[0].strip() for d in deps}


def test_core_dependency_is_psycopg_binary():
    names = _names(PYPROJECT["project"]["dependencies"])
    assert "psycopg[binary]" in names
    assert "psycopg[c]" not in names


def test_compiled_psycopg_is_an_optional_extra():
    extras = PYPROJECT["project"].get("optional-dependencies", {})
    assert "psycopg[c]" in _names(extras.get("c", []))
