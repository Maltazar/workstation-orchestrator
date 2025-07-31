import pytest
from models.base.command import (
    Command,
    CommandExecution,
    CommandGroup,
    CommandModel,
    ShellType,
)
from models.base.os_type import OSType


def test_command_execution_from_string():
    """Test creating CommandExecution from string"""
    cmd = CommandExecution(run="echo 'hello'")
    assert cmd.run == "echo 'hello'"
    assert cmd.args is None
    assert not cmd.fail_on_error
    assert cmd.valid_exit_codes is None
    assert cmd.saved_output_name is None
    assert not cmd.elevate


def test_command_execution_create_command():
    """Test creating command string with shell command"""
    cmd = CommandExecution(run="echo", args=["hello", "world"])
    result = cmd.create_command("bash -c")
    assert result == 'bash -c "echo hello world"'


def test_command_group_conversion():
    """Test converting legacy command format to CommandGroup"""
    legacy_format = {
        "test_group": [{"shell": "bash", "execute": ["echo 'hello'", "echo 'world'"]}]
    }

    model = CommandModel(root=legacy_format)
    assert "test_group" in model.root
    assert isinstance(model.root["test_group"], CommandGroup)
    assert len(model.root["test_group"].commands) == 1
    assert len(model.root["test_group"].commands[0].execute) == 2


def test_shell_type_validation():
    """Test shell type validation for different OS types"""
    command = Command(shell=ShellType.POWERSHELL, execute=["Write-Host 'Hello'"])

    # Should be valid for Windows
    windows_os = OSType(windows=True)
    valid_shells = command.validate_shell_type(windows_os)
    assert ShellType.POWERSHELL in valid_shells

    # Should not be valid for Linux
    linux_os = OSType(linux=True)
    valid_shells = command.validate_shell_type(linux_os)
    assert ShellType.POWERSHELL not in valid_shells


def test_command_execution_with_saved_output():
    """Test command execution with output saving"""
    cmd = CommandExecution(run="echo 'test'", saved_output_name="test_output")
    assert cmd.saved_output_name == "test_output"
    assert cmd.create_command("bash -c") == "bash -c \"echo 'test'\""


def test_command_execution_with_valid_exit_codes():
    """Test command execution with custom valid exit codes"""
    cmd = CommandExecution(run="test_cmd", valid_exit_codes=[0, 1])
    assert 0 in cmd.valid_exit_codes
    assert 1 in cmd.valid_exit_codes


def test_multiline_command():
    """Test handling of multiline commands"""
    multiline_cmd = "echo 'line 1' && echo 'line 2'"
    cmd = CommandExecution(run=multiline_cmd)
    result = cmd.create_command("bash -c")
    assert "line 1" in result
    assert "line 2" in result
    assert result.startswith('bash -c "')
    assert result.endswith('"')
