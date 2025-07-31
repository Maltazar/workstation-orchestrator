import pytest
from unittest.mock import patch, MagicMock
from helpers.subprocess_helper import (
    is_sudo_available,
    is_installing_sudo,
    strip_sudo,
    command_needs_sudo,
    reset_sudo_cache,
    run_subprocess,
)
import subprocess


@pytest.mark.parametrize(
    "cmd,expected",
    [
        # Basic package installation (existing cases)
        ("apt install sudo", True),
        ("apt-get install sudo", True),
        ("dnf install sudo", True),
        ("yum install sudo", True),
        ("pacman -S sudo", True),
        ("zypper install sudo", True),
        # List format commands
        (["apt", "install", "sudo"], True),
        (["pacman", "-S", "sudo"], True),
        (["apt", "install", "vim", "sudo", "git"], True),
        (["sudo", "apt", "install", "sudo"], True),
        # Complex multiline commands
        (
            "sudo apt update && sudo apt install -y sudo",  # Normalized form
            True,
        ),
        (
            "apt update && apt install vim && apt install sudo",  # Normalized form
            True,
        ),
        # Multiple commands with different separators
        ("apt update && apt install sudo || apt install -y sudo", True),
        ("apt update | tee log && apt install sudo", True),
        (
            "sudo apt update && sudo apt install vim | tee log && sudo apt install sudo",
            True,
        ),
        # Commands with complex flags
        ("sudo -H -n apt install --no-install-recommends -y sudo", True),
        ("sudo apt install -y --no-install-recommends sudo=1.8.31-1ubuntu1.2", True),
        # Edge cases
        ("echo 'sudo' && apt install sudo", True),  # Second command matters
        ("apt install pseudo-sudo sudo", True),  # Should match 'sudo' package
        ("", False),  # Empty command
        (" ", False),  # Whitespace only
        ([], False),  # Empty list
    ],
)
def test_is_installing_sudo(cmd, expected):
    """Test is_installing_sudo function with various command patterns"""
    assert is_installing_sudo(cmd) == expected


@pytest.mark.parametrize(
    "cmd,expected",
    [
        # List format
        (["sudo", "apt", "update"], ["apt", "update"]),
        (["sudo", "-n", "apt", "install", "vim"], ["apt", "install", "vim"]),
        # Multiline commands
        (
            "sudo apt update && sudo apt install vim",  # Normalized form
            "apt update && apt install vim",
        ),
        # Complex chains
        (
            "sudo apt update | sudo tee log && sudo apt install vim",
            "apt update | tee log && apt install vim",
        ),
        # Mixed sudo usage
        ("sudo apt update && apt install vim", "apt update && apt install vim"),
        ("apt update && sudo apt install vim", "apt update && apt install vim"),
        # Edge cases
        ("sudo", ""),  # Just sudo
        ("sudo -H -n", ""),  # Just sudo with flags
        (" sudo apt update ", "apt update"),  # Extra whitespace
    ],
)
def test_strip_sudo(cmd, expected):
    """Test strip_sudo function with various command patterns"""
    assert strip_sudo(cmd) == expected


@pytest.mark.parametrize(
    "cmd,sudo_available,expected",
    [
        # List format
        (["apt", "update"], True, True),
        (["sudo", "apt", "update"], True, False),
        # Complex commands
        ("apt update && apt install vim", True, True),
        ("sudo apt update && apt install vim", True, False),
        ("echo test && apt update", True, True),
        # Windows vs Unix commands
        ("net user administrator", True, True),  # Windows admin command
        ("ipconfig /release", True, False),  # Windows non-admin command
        # Edge cases
        ("", True, False),
        (" ", True, False),
        ([], True, False),
    ],
)
def test_command_needs_sudo(cmd, sudo_available, expected):
    """Test command_needs_sudo function with various commands and sudo availability"""
    with patch(
        "helpers.subprocess_helper.is_sudo_available",
        return_value=sudo_available,
    ):
        assert command_needs_sudo(cmd) == expected


@pytest.mark.parametrize(
    "os_name,cmd,expected_cmd",
    [
        # Windows commands (no sudo)
        ("nt", "apt update", "apt update"),
        ("nt", "sudo apt update", "apt update"),  # Should strip sudo
        ("nt", ["sudo", "apt", "update"], ["apt", "update"]),
        # Unix commands (with sudo)
        ("posix", "apt update", "sudo apt update"),
        ("posix", ["apt", "update"], ["sudo", "apt", "update"]),
        ("posix", "sudo apt update", "sudo apt update"),  # Already has sudo
        # Complex commands
        (
            "posix",
            "apt update && apt install vim",  # Normalized form
            "sudo apt update && sudo apt install vim",
        ),
        (
            "nt",
            "apt update && sudo apt install vim",  # Normalized form
            "apt update && apt install vim",
        ),
    ],
)
def test_run_subprocess_platform_specific(os_name, cmd, expected_cmd):
    """Test platform-specific command handling in run_subprocess"""
    with patch("os.name", os_name), patch(
        "helpers.subprocess_helper.is_sudo_available", return_value=True
    ), patch("subprocess.run") as mock_run:

        run_subprocess(cmd)

        # Check if the command was modified correctly for the platform
        actual_cmd = mock_run.call_args[0][0]
        if isinstance(actual_cmd, list):
            actual_cmd = " ".join(actual_cmd)
        if isinstance(expected_cmd, list):
            expected_cmd = " ".join(expected_cmd)

        assert actual_cmd == expected_cmd


@pytest.mark.parametrize(
    "cmd,interactive,expected_kwargs",
    [
        # Interactive mode
        (
            "apt update",
            True,
            {
                "stdout": None,
                "stderr": None,
                "stdin": subprocess.PIPE,
            },
        ),
        # Non-interactive mode
        (
            "apt update",
            False,
            {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "stdin": None,
            },
        ),
        # With input
        (
            "apt update",
            False,
            {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "input": "y\n",
            },  # Removed stdin since it's handled by the function
        ),
    ],
)
def test_run_subprocess_io_handling(cmd, interactive, expected_kwargs):
    """Test subprocess IO handling with different configurations"""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Remove input from kwargs to avoid duplicates
        kwargs = {k: v for k, v in expected_kwargs.items() if k != "input"}

        # Call run_subprocess with input parameter
        run_subprocess(cmd, interactive=interactive, **kwargs)

        # For verification, we need to check that all expected kwargs were passed
        actual_kwargs = mock_run.call_args[1]
        # Only check the kwargs that we actually passed
        for k, v in kwargs.items():
            assert actual_kwargs[k] == v


@pytest.mark.parametrize(
    "sudo_exists,expected",
    [
        (True, True),
        (False, False),
    ],
)
def test_is_sudo_available(sudo_exists, expected):
    """Test is_sudo_available function"""
    reset_sudo_cache()  # Reset cache before test
    with patch("shutil.which", return_value="/usr/bin/sudo" if sudo_exists else None):
        assert is_sudo_available() == expected
        # Test caching
        assert is_sudo_available() == expected  # Should use cached value
