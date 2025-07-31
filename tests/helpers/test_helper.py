import pytest
from unittest.mock import patch, MagicMock
from helpers.helper import (
    download_config,
    download_resource,
    merge_yaml,
    get_host_os,
    get_linux_os_dist,
    is_same_linux_dist,
    get_current_shell,
    update_shell_config,
)
from models.base.resources import DownloadResource
from models.config import Configuration
from models.base.os_type import OSType
from models.base.command import ShellType


def test_download_config():
    """Test download_config function"""
    with patch("helpers.helper.download_resource") as mock_download:
        url = "http://example.com/config.yaml"
        result = download_config(url)

        # Verify correct path construction
        assert result == "downloads/config.yaml"

        # Verify download_resource was called correctly
        mock_download.assert_called_once()
        resource_arg = mock_download.call_args[0][0]
        assert isinstance(resource_arg, DownloadResource)
        assert resource_arg.url == url
        assert resource_arg.path == "downloads/config.yaml"


def test_download_resource():
    """Test download_resource function"""
    with patch("requests.get") as mock_get, patch(
        "pathlib.Path.mkdir"
    ) as mock_mkdir, patch("builtins.open", create=True) as mock_open:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_get.return_value = mock_response

        # Setup mock file
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create test resource
        resource = DownloadResource(
            url="http://example.com/test.txt", path="downloads/test.txt"
        )

        # Call function
        download_resource(resource)

        # Verify directory creation
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify file writing
        mock_open.assert_called_once_with("downloads/test.txt", "wb")
        mock_file.write.assert_called_once_with(b"test content")


def test_get_current_shell():
    """Test shell detection"""
    with patch("helpers.helper.run_subprocess") as mock_run:
        # Test zsh detection
        mock_run.return_value.stdout = "/bin/zsh\n"
        shell, config = get_current_shell()
        assert shell == "/bin/zsh"
        assert config == "~/.zshrc"

        # Test bash detection
        mock_run.return_value.stdout = "/bin/bash\n"
        shell, config = get_current_shell()
        assert shell == "/bin/bash"
        assert config == "~/.bashrc"


def test_update_shell_config():
    """Test shell config file updates"""
    with patch("builtins.open", create=True) as mock_open, patch(
        "os.path.exists"
    ) as mock_exists, patch("os.path.expanduser") as mock_expanduser, patch(
        "helpers.helper.get_current_shell"
    ) as mock_get_shell:

        # Setup mocks
        mock_exists.return_value = True
        mock_expanduser.return_value = "/home/user/.bashrc"
        mock_get_shell.return_value = ("/bin/bash", "~/.bashrc")
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = "existing content"

        # Test adding new config
        result = update_shell_config("export PATH=$PATH:/new/path", "# New path")
        assert result == True
        mock_open.assert_any_call("/home/user/.bashrc", "a")

        # Test duplicate config prevention
        mock_file.read.return_value = "# New path\nexport PATH=$PATH:/new/path"
        result = update_shell_config("export PATH=$PATH:/new/path", "# New path")
        assert result == True  # Should succeed but not modify file


def test_get_host_os():
    """Test OS detection"""
    with patch("platform.system") as mock_system:
        # Test Windows detection
        mock_system.return_value = "Windows"
        os_type = get_host_os()
        assert os_type.windows == True

        # Test Linux detection
        mock_system.return_value = "Linux"
        os_type = get_host_os()
        assert os_type.linux == True

        # Test Mac detection
        mock_system.return_value = "Darwin"
        os_type = get_host_os()
        assert os_type.mac == True


def test_is_same_linux_dist():
    """Test Linux distribution comparison"""
    with patch("helpers.helper.get_linux_os_dist") as mock_get_dist:
        # Test Debian family
        mock_get_dist.return_value = "ubuntu"
        assert is_same_linux_dist("debian") == True
        assert is_same_linux_dist("ubuntu") == True
        assert is_same_linux_dist("fedora") == False

        # Test Fedora family
        mock_get_dist.return_value = "fedora"
        assert is_same_linux_dist("fedora") == True
        assert is_same_linux_dist("rocky") == True
        assert is_same_linux_dist("debian") == False


def test_merge_yaml():
    """Test YAML configuration merging"""
    with patch("builtins.open", create=True) as mock_open, patch(
        "pathlib.Path.exists"
    ) as mock_exists:
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = """
command:
  test:
    - shell: bash
      execute: ["echo test"]
os:
  windows: false
  linux: true
  mac: false
  wsl: false
"""

        base_config = Configuration(os=OSType(linux=True))
        result = merge_yaml("test.yaml", base_config)

        assert result.os.linux == True
        assert "test" in result.command.root
        assert (
            result.command.root["test"].commands[0].shell == ShellType.BASH
        )  # Fixed access to CommandGroup


# Add more tests for other helper functions...
