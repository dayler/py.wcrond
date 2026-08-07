import os
import re

base_dir = r"c:\Users\as116758\dev\wcron"

dirs = [
    "src/wcrond",
    "src/wcrond_ctl",
    "tests",
    "examples",
    "scripts"
]

for d in dirs:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

files = {
    "pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "wcrond"
version = "1.0.0"
description = "Windows Cron Daemon"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "croniter",
    "pywin32",
    "tomli; python_version < '3.11'"
]

[project.optional-dependencies]
dev = [
    "pytest"
]

[project.scripts]
wcrond = "wcrond.__main__:main"
wcrond-ctl = "wcrond_ctl.__main__:main"
""",
    "README.md": "# wcrond\nWindows Cron Daemon\n",
    "LICENSE": "MIT License\n",
    "src/wcrond/__init__.py": "__version__ = \"1.0.0\"\n",
    "src/wcrond/__main__.py": "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n",
    "src/wcrond/daemon.py": '"""WcrondDaemon module."""\n',
    "src/wcrond/scheduler.py": '"""Scheduler module."""\n',
    "src/wcrond/job.py": '"""Job module."""\n',
    "src/wcrond/parser.py": '"""Parser module."""\n',
    "src/wcrond/executor.py": '"""Executor module."""\n',
    "src/wcrond/retry.py": '"""Retry module."""\n',
    "src/wcrond/watchdog.py": '"""Watchdog module."""\n',
    "src/wcrond/state.py": '"""State module."""\n',
    "src/wcrond/ipc.py": '"""IPC module."""\n',
    "src/wcrond/config.py": '"""Config module."""\n',
    "src/wcrond/logging_config.py": '"""Logging config module."""\n',
    "src/wcrond_ctl/__init__.py": "",
    "src/wcrond_ctl/__main__.py": "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n",
    "src/wcrond_ctl/cli.py": '"""CLI module."""\n',
    "src/wcrond_ctl/client.py": '"""Client module."""\n',
    "src/wcrond_ctl/formatters.py": '"""Formatters module."""\n',
    "tests/__init__.py": "",
    "tests/test_structure.py": """import pytest

def test_import_wcrond():
    import wcrond
    assert wcrond is not None

def test_import_wcrond_ctl():
    import wcrond_ctl
    assert wcrond_ctl is not None

def test_version():
    import wcrond
    assert wcrond.__version__ == "1.0.0"

def test_entry_points():
    import wcrond.__main__
    import wcrond_ctl.__main__
    assert hasattr(wcrond.__main__, 'main')
    assert hasattr(wcrond_ctl.__main__, 'main')
""",
    "scripts/install.ps1": "# Install script\npip install -e .\n",
    "scripts/uninstall.ps1": "# Uninstall script\npip uninstall -y wcrond\n"
}

for rel_path, content in files.items():
    with open(os.path.join(base_dir, rel_path), "w", encoding="utf-8") as f:
        f.write(content)

with open(os.path.join(base_dir, 'planing/wcrond_prd.md'), 'r', encoding='utf-8') as f:
    prd_content = f.read()

wcrond_toml = re.search(r'### 6\.1 Configuración del Sistema — `wcrond\.toml`\s*```toml\n(.*?)```', prd_content, re.DOTALL).group(1)
wcrontab_toml = re.search(r'### 6\.2 Definición de Jobs — `wcrontab\.toml`\s*```toml\n(.*?)```', prd_content, re.DOTALL).group(1)

with open(os.path.join(base_dir, 'examples/wcrond.toml'), 'w', encoding='utf-8') as f:
    f.write(wcrond_toml)

with open(os.path.join(base_dir, 'examples/wcrontab.toml'), 'w', encoding='utf-8') as f:
    f.write(wcrontab_toml)

print("Files created successfully.")
