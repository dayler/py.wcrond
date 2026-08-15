import pytest
import os
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from wcrond.autostart import (
    install_autostart,
    uninstall_autostart,
    is_autostart_installed,
    get_wcrond_command,
    _find_wcrond_exe,
    REGISTRY_KEY,
    REGISTRY_VALUE_NAME,
    STARTUP_SHORTCUT_NAME,
)


class TestGetWcrondCommand:
    @patch("wcrond.autostart._find_wcrond_exe")
    def test_with_exe_found(self, mock_find):
        mock_find.return_value = "C:\\Python\\Scripts\\wcrond.exe"
        result = get_wcrond_command()
        assert result == '"C:\\Python\\Scripts\\wcrond.exe" start'

    @patch("wcrond.autostart._find_wcrond_exe")
    def test_fallback_to_python(self, mock_find):
        mock_find.return_value = None
        result = get_wcrond_command()
        assert "-m wcrond start" in result
        assert "python" in result.lower() or "sys.executable" in result

    @patch("shutil.which")
    def test_find_exe_via_which(self, mock_which):
        mock_which.return_value = "C:\\tools\\wcrond.exe"
        result = _find_wcrond_exe()
        assert result == "C:\\tools\\wcrond.exe"

    @patch("shutil.which")
    def test_find_exe_not_found(self, mock_which):
        mock_which.return_value = None
        # Also ensure the Scripts path doesn't exist
        with patch("wcrond.autostart.Path.exists", return_value=False):
            result = _find_wcrond_exe()
        assert result is None


class TestInstallAutostart:
    @patch("wcrond.autostart._install_registry")
    def test_install_registry(self, mock_install):
        mock_install.return_value = True
        assert install_autostart("registry") is True
        mock_install.assert_called_once()

    @patch("wcrond.autostart._install_startup_folder")
    def test_install_startup(self, mock_install):
        mock_install.return_value = True
        assert install_autostart("startup") is True
        mock_install.assert_called_once()

    def test_install_invalid_method(self):
        with pytest.raises(ValueError, match="Unknown auto-start method"):
            install_autostart("invalid_method")


class TestRegistryAutostart:
    @patch("wcrond.autostart.winreg")
    @patch("wcrond.autostart.get_wcrond_command")
    def test_install_registry_success(self, mock_cmd, mock_winreg):
        mock_cmd.return_value = '"wcrond.exe" start'
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_SET_VALUE = 0x0002
        mock_winreg.REG_SZ = 1

        from wcrond.autostart import _install_registry
        assert _install_registry() is True

        mock_winreg.SetValueEx.assert_called_once_with(
            mock_key, REGISTRY_VALUE_NAME, 0, mock_winreg.REG_SZ, '"wcrond.exe" start'
        )
        mock_winreg.CloseKey.assert_called_once_with(mock_key)

    @patch("wcrond.autostart.winreg")
    def test_install_registry_failure(self, mock_winreg):
        mock_winreg.OpenKey.side_effect = OSError("Access denied")
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_SET_VALUE = 0x0002

        from wcrond.autostart import _install_registry
        assert _install_registry() is False

    @patch("wcrond.autostart.winreg")
    def test_uninstall_registry_success(self, mock_winreg):
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_SET_VALUE = 0x0002

        from wcrond.autostart import _uninstall_registry
        assert _uninstall_registry() is True

        mock_winreg.DeleteValue.assert_called_once_with(mock_key, REGISTRY_VALUE_NAME)

    @patch("wcrond.autostart.winreg")
    def test_uninstall_registry_not_found(self, mock_winreg):
        mock_winreg.OpenKey.side_effect = FileNotFoundError
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_SET_VALUE = 0x0002

        from wcrond.autostart import _uninstall_registry
        assert _uninstall_registry() is False

    @patch("wcrond.autostart.winreg")
    def test_check_registry_installed(self, mock_winreg):
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_READ = 0x20019
        mock_winreg.QueryValueEx.return_value = ('"wcrond.exe" start', 1)

        from wcrond.autostart import _check_registry
        assert _check_registry() is True

    @patch("wcrond.autostart.winreg")
    def test_check_registry_not_installed(self, mock_winreg):
        mock_winreg.OpenKey.side_effect = FileNotFoundError
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.KEY_READ = 0x20019

        from wcrond.autostart import _check_registry
        assert _check_registry() is False


class TestStartupFolderAutostart:
    def test_uninstall_startup_folder_exists(self, tmp_path):
        lnk = tmp_path / STARTUP_SHORTCUT_NAME
        lnk.write_text("shortcut")

        with patch("wcrond.autostart._get_startup_folder", return_value=tmp_path):
            from wcrond.autostart import _uninstall_startup_folder
            assert _uninstall_startup_folder() is True
            assert not lnk.exists()

    def test_uninstall_startup_folder_not_exists(self, tmp_path):
        with patch("wcrond.autostart._get_startup_folder", return_value=tmp_path):
            from wcrond.autostart import _uninstall_startup_folder
            assert _uninstall_startup_folder() is False

    def test_check_startup_folder_exists(self, tmp_path):
        lnk = tmp_path / STARTUP_SHORTCUT_NAME
        lnk.write_text("shortcut")

        with patch("wcrond.autostart._get_startup_folder", return_value=tmp_path):
            from wcrond.autostart import _check_startup_folder
            assert _check_startup_folder() is True

    def test_check_startup_folder_not_exists(self, tmp_path):
        with patch("wcrond.autostart._get_startup_folder", return_value=tmp_path):
            from wcrond.autostart import _check_startup_folder
            assert _check_startup_folder() is False


class TestUninstallAutostart:
    @patch("wcrond.autostart._uninstall_startup_folder")
    @patch("wcrond.autostart._uninstall_registry")
    def test_uninstall_both(self, mock_reg, mock_startup):
        mock_reg.return_value = True
        mock_startup.return_value = True
        assert uninstall_autostart() is True

    @patch("wcrond.autostart._uninstall_startup_folder")
    @patch("wcrond.autostart._uninstall_registry")
    def test_uninstall_none(self, mock_reg, mock_startup):
        mock_reg.return_value = False
        mock_startup.return_value = False
        assert uninstall_autostart() is False

    @patch("wcrond.autostart._uninstall_startup_folder")
    @patch("wcrond.autostart._uninstall_registry")
    def test_uninstall_only_registry(self, mock_reg, mock_startup):
        mock_reg.return_value = True
        mock_startup.return_value = False
        assert uninstall_autostart() is True


class TestIsAutostartInstalled:
    @patch("wcrond.autostart._check_startup_folder")
    @patch("wcrond.autostart._check_registry")
    def test_returns_dict(self, mock_reg, mock_startup):
        mock_reg.return_value = True
        mock_startup.return_value = False
        result = is_autostart_installed()
        assert result == {"registry": True, "startup_folder": False}

    @patch("wcrond.autostart._check_startup_folder")
    @patch("wcrond.autostart._check_registry")
    def test_both_installed(self, mock_reg, mock_startup):
        mock_reg.return_value = True
        mock_startup.return_value = True
        result = is_autostart_installed()
        assert result == {"registry": True, "startup_folder": True}
