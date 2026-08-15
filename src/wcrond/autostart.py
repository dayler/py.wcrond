"""Auto-start management for wcrond on Windows.

Provides functions to register/unregister wcrond for automatic
start at user login via Windows Registry or Startup folder.
"""

import sys
import os
import logging
import winreg
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REGISTRY_VALUE_NAME = "wcrond"
STARTUP_SHORTCUT_NAME = "wcrond.lnk"


def get_wcrond_command() -> str:
    """Build the command string to launch wcrond in background."""
    wcrond_exe = _find_wcrond_exe()
    if wcrond_exe:
        return f'"{wcrond_exe}" start'
    return f'"{sys.executable}" -m wcrond start'


def _find_wcrond_exe() -> str | None:
    """Try to locate the wcrond executable in PATH/Scripts."""
    import shutil
    exe = shutil.which("wcrond")
    if exe:
        return exe
    # Check common locations
    scripts_dir = Path(sys.prefix) / "Scripts" / "wcrond.exe"
    if scripts_dir.exists():
        return str(scripts_dir)
    return None


def install_autostart(method: str = "registry") -> bool:
    """Register wcrond for auto-start at user login.
    
    Args:
        method: 'registry' for HKCU Run key, 'startup' for Startup folder shortcut.
    
    Returns:
        True if registration succeeded.
    
    Raises:
        ValueError: If method is not 'registry' or 'startup'.
    """
    if method == "registry":
        return _install_registry()
    elif method == "startup":
        return _install_startup_folder()
    else:
        raise ValueError(f"Unknown auto-start method: {method}")


def uninstall_autostart() -> bool:
    """Remove wcrond from all auto-start mechanisms.
    
    Returns:
        True if at least one mechanism was removed.
    """
    r1 = _uninstall_registry()
    r2 = _uninstall_startup_folder()
    return r1 or r2


def is_autostart_installed() -> dict:
    """Check which auto-start methods are configured.
    
    Returns:
        Dict with keys 'registry' and 'startup_folder', each a bool.
    """
    return {
        "registry": _check_registry(),
        "startup_folder": _check_startup_folder(),
    }


# --- Registry methods ---

def _install_registry() -> bool:
    """Register wcrond in HKCU\\...\\Run for auto-start at login."""
    cmd = get_wcrond_command()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, REGISTRY_VALUE_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        logger.info(f"Registered auto-start via registry: {cmd}")
        return True
    except OSError as e:
        logger.error(f"Failed to register auto-start in registry: {e}")
        return False


def _uninstall_registry() -> bool:
    """Remove wcrond from HKCU\\...\\Run."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, REGISTRY_VALUE_NAME)
        winreg.CloseKey(key)
        logger.info("Removed auto-start from registry")
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        logger.error(f"Failed to remove auto-start from registry: {e}")
        return False


def _check_registry() -> bool:
    """Check if wcrond is registered in HKCU\\...\\Run."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, REGISTRY_VALUE_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


# --- Startup folder methods ---

def _get_startup_folder() -> Path:
    """Get the Windows Startup folder path."""
    return Path(os.environ.get("APPDATA", "")) / (
        "Microsoft" / Path("Windows") / "Start Menu" / "Programs" / "Startup"
    )


def _install_startup_folder() -> bool:
    """Create a shortcut in the Windows Startup folder."""
    try:
        import win32com.client
        startup = _get_startup_folder()
        lnk_path = str(startup / STARTUP_SHORTCUT_NAME)

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)

        wcrond_exe = _find_wcrond_exe()
        if wcrond_exe:
            shortcut.TargetPath = wcrond_exe
            shortcut.Arguments = "start"
        else:
            shortcut.TargetPath = sys.executable
            shortcut.Arguments = "-m wcrond start"

        shortcut.WindowStyle = 7  # Minimized
        shortcut.save()
        logger.info(f"Created startup shortcut: {lnk_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create startup shortcut: {e}")
        return False


def _uninstall_startup_folder() -> bool:
    """Remove the wcrond shortcut from the Startup folder."""
    lnk = _get_startup_folder() / STARTUP_SHORTCUT_NAME
    if lnk.exists():
        lnk.unlink()
        logger.info(f"Removed startup shortcut: {lnk}")
        return True
    return False


def _check_startup_folder() -> bool:
    """Check if wcrond shortcut exists in the Startup folder."""
    return (_get_startup_folder() / STARTUP_SHORTCUT_NAME).exists()
