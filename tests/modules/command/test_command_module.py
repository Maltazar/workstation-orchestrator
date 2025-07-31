import pytest
from unittest.mock import MagicMock, patch
from models.base.command import Command, CommandExecution, ShellType
from models.base.os_type import OSType
from modules.command.command import run_commands
from models.base.output_store import OutputStore


@pytest.fixture
def mock_subprocess(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("modules.command.command.run_subprocess", mock)
    return mock


@pytest.fixture
def mock_host_os(monkeypatch):
    mock = MagicMock()
    mock.return_value = OSType(linux=True)
    monkeypatch.setattr("modules.command.command.get_host_os", mock)
    return mock


def test_run_commands_basic(mock_subprocess, mock_host_os):
    """Test basic command execution"""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "test output"
    mock_subprocess.return_value = mock_process

    command = Command(
        shell=ShellType.BASH, execute=[CommandExecution(run="echo 'Hello'")]
    )

    # Run command
    run_commands("test_group", [command])

    # Verify subprocess was called
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "echo 'Hello'" in call_args


def test_run_commands_with_error(mock_subprocess, mock_host_os):
    """Test command execution with error"""
    # Setup
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "error message"
    mock_subprocess.side_effect = Exception(
        "Command failed"
    )  # Change to raise exception

    # Create test command with fail_on_error=True
    command = Command(
        shell=ShellType.BASH,
        execute=[CommandExecution(run="false", fail_on_error=True)],
    )

    # Run command and expect exception
    with pytest.raises(Exception):
        run_commands("test_group", [command])


def test_run_commands_with_output_save(mock_subprocess, mock_host_os):
    """Test command execution with output saving"""
    # Setup
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "test output"
    mock_subprocess.return_value = mock_process

    # Create test command with output saving
    command = Command(
        shell=ShellType.BASH,
        execute=[CommandExecution(run="echo 'Hello'", saved_output_name="test_output")],
    )

    # Run command
    run_commands("test_group", [command])

    store = OutputStore.get_instance()
    assert store.get_output("test_output") == "test output"


def test_run_commands_with_custom_exit_codes(mock_subprocess, mock_host_os):
    """Test command execution with custom valid exit codes"""
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_subprocess.return_value = mock_process

    command = Command(
        shell=ShellType.BASH,
        execute=[CommandExecution(run="false", valid_exit_codes=[0, 1])],
    )

    # Should not raise exception since exit code 1 is valid
    run_commands("test_group", [command])


@pytest.fixture(autouse=True)
def clear_output_store():
    """Clear the OutputStore before and after each test"""
    OutputStore._instance = None
    yield
    OutputStore._instance = None


@patch("platform.system")
@patch("helpers.helper.get_linux_os_dist")
def test_run_commands_with_multiline_heredoc(
    mock_get_linux_os_dist, mock_platform, mock_subprocess, mock_host_os
):
    """Test execution of multiline commands with heredoc syntax"""
    # Setup Linux platform
    mock_platform.return_value = "Linux"
    mock_get_linux_os_dist.return_value = "ubuntu"
    # Setup subprocess mock
    mock_process = MagicMock()
    mock_process.returncode = 1  # Should fail like in real output
    mock_process.stderr = "/bin/sh: line 1: warning: here-document at line 1 delimited by end-of-file (wanted `EOL')"
    mock_subprocess.return_value = mock_process

    # Create test command with heredoc - exactly as used in the real command
    heredoc_command = """DESKTOP_FILE="/usr/share/applications/cursor.desktop"
cat <<EOL | sudo tee "$DESKTOP_FILE"
[Desktop Entry]
Name=Cursor
Exec=$INSTALL_DIR
Type=Application
Terminal=false
Icon=/usr/share/icons/cursor-icon.png
Categories=Utility;
EOL"""

    command = Command(
        shell=ShellType.BASH,
        os_dist="ubuntu",
        execute=[CommandExecution(run=heredoc_command)],
    )

    # Run command
    run_commands("test_group", [command])

    # Verify subprocess was called correctly
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args

    # Check that shell=True was passed to run_subprocess
    assert call_args[1]["shell"] is True

    # The actual command string should be passed through exactly
    cmd = call_args[0][0]

    # Verify the command structure
    assert "DESKTOP_FILE=" in cmd
    assert "cat <<EOL" in cmd
    assert "[Desktop Entry]" in cmd
    assert "Categories=Utility;" in cmd
    assert "EOL" in cmd  # The closing EOL tag should be present
