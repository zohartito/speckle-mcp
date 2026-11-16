"""Offline checks for the supported installation contract."""

from importlib.metadata import metadata
from pathlib import Path
import tomllib

from packaging.specifiers import SpecifierSet


ROOT = Path(__file__).resolve().parents[1]


def test_python_minimum_matches_specklepy():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    supported = SpecifierSet(project["requires-python"])
    sdk_supported = SpecifierSet(metadata("specklepy")["Requires-Python"])
    assert "3.10" not in sdk_supported
    assert "3.10" not in supported, "Python 3.10 cannot install the required specklepy"
    assert "3.11" in supported and "3.11" in sdk_supported
    assert "Python 3.11+" in (ROOT / "README.md").read_text()
    assert 'python-version: "3.11"' in (ROOT / ".github/workflows/ci.yml").read_text()
