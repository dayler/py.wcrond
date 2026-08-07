from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import shutil
import sys
from pathlib import Path

def setup_wcrond_config():
    try:
        user_profile = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        base_dir = Path(user_profile) / '.wcrond'
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine the source directory for examples
        # setup.py is run from the project root
        project_root = Path(__file__).parent.absolute()
        examples_dir = project_root / 'examples'
        
        wcrond_toml_src = examples_dir / 'wcrond.toml'
        wcrontab_init_src = examples_dir / 'wcrontab.init.toml'
        
        wcrond_conf = base_dir / 'wcrond.toml'
        if wcrond_toml_src.exists() and not wcrond_conf.exists():
            shutil.copy(wcrond_toml_src, wcrond_conf)
            print(f"Copied default config to {wcrond_conf}")
            
        wcrontab_conf = base_dir / 'wcrontab.toml'
        if wcrontab_init_src.exists() and not wcrontab_conf.exists():
            shutil.copy(wcrontab_init_src, wcrontab_conf)
            print(f"Copied default job config to {wcrontab_conf}")
            
        (base_dir / 'jobs.d').mkdir(exist_ok=True)
        (base_dir / 'logs').mkdir(exist_ok=True)
        print("wcrond initial configuration generated successfully.")
    except Exception as e:
        print(f"Warning: Failed to generate initial configuration: {e}")

class CustomInstallCommand(install):
    def run(self):
        install.run(self)
        setup_wcrond_config()

class CustomDevelopCommand(develop):
    def run(self):
        develop.run(self)
        setup_wcrond_config()

setup(
    cmdclass={
        'install': CustomInstallCommand,
        'develop': CustomDevelopCommand,
    },
)
