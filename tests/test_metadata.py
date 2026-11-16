"""Offline checks for the supported installation contract."""

from importlib.metadata import metadata
from pathlib import Path
import re
import tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


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


def test_dependency_and_build_closure_is_hash_locked():
    lock = ROOT / "requirements-dev.lock"
    assert lock.exists(), "Runtime, build and audit dependencies need a hash-locked closure"
    entries = [line.strip() for line in lock.read_text().replace("\\\n", " ").splitlines()
               if line.strip() and not line.startswith("#")]
    locked = {}
    for entry in entries:
        requirement, *hashes = entry.split(" --hash=")
        req = Requirement(requirement.strip())
        assert len(list(req.specifier)) == 1 and next(iter(req.specifier)).operator == "=="
        assert hashes and all(re.fullmatch(r"sha256:[0-9a-f]{64}", item.strip()) for item in hashes)
        locked[canonicalize_name(req.name)] = req.specifier
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = (config["project"]["dependencies"] + config["project"]["optional-dependencies"]["dev"]
                    + config["build-system"]["requires"])
    for requirement in requirements:
        req = Requirement(requirement)
        pin = locked[canonicalize_name(req.name)]
        assert next(iter(pin)).version in req.specifier
    assert "pip-audit" in locked
    assert "editables" in locked, "hatchling needs editables to build the editable install"
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "--require-hashes -r requirements-dev.lock" in ci
    assert "--no-deps --no-build-isolation -e ." in ci
    assert "pip_audit" in ci and "--no-deps" in ci
