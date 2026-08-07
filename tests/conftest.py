import pytest
import os
from pathlib import Path

@pytest.fixture
def temp_home(tmp_path):
    old_home = os.environ.get("USERPROFILE")
    os.environ["USERPROFILE"] = str(tmp_path)
    yield tmp_path
    if old_home is None:
        del os.environ["USERPROFILE"]
    else:
        os.environ["USERPROFILE"] = old_home

@pytest.fixture
def wcrond_dir(temp_home):
    d = temp_home / ".wcrond"
    d.mkdir(parents=True, exist_ok=True)
    return d
