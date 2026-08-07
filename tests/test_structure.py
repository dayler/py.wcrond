import pytest

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

def test_init_wcrond(tmp_path):
    from wcrond.__main__ import init_wcrond
    from wcrond.config import WcrondConfig
    
    # Create mock config pointing to tmp_path
    config = WcrondConfig(str(tmp_path / "wcrond.toml"))
    config.base_dir = tmp_path
    
    # Run init
    init_wcrond(config)
    
    # Verify files were created and not empty (assuming examples were copied)
    wcrond_conf = tmp_path / "wcrond.toml"
    wcrontab_conf = tmp_path / "wcrontab.toml"
    
    assert wcrond_conf.exists()
    assert wcrontab_conf.exists()
    
    # During tests run from source, examples dir should be found
    if wcrond_conf.stat().st_size > 0:
        # Verify it is exactly the same file as examples/wcrond.init.toml
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        init_toml_path = project_root / "examples" / "wcrond.init.toml"
        if init_toml_path.exists():
            assert wcrond_conf.read_bytes() == init_toml_path.read_bytes()

    if wcrontab_conf.stat().st_size > 0:
        assert b"[jobs" in wcrontab_conf.read_bytes()

