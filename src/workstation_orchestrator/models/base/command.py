from typing import Dict, List, Optional, Union, Any
from pydantic import RootModel, model_validator
from enum import Enum
from models.base_model import BaseConfigModel, ExecutionOrder
from models.base.os_type import OSType
from logger.logger import logger
from models.base.output_store import OutputStore
import platform
from models.base.resources import GroupedResources


class ShellType(Enum):
    SH = "sh"
    BASH = "bash"
    BAT = "bat"
    CMD = "cmd"
    POWERSHELL = "powershell"
    ZSH = "zsh"
    FISH = "fish"

    @classmethod
    def get_os_shell_types(cls) -> Dict[str, List["ShellType"]]:
        return {
            "windows": [cls.CMD, cls.BAT, cls.POWERSHELL],
            "linux": [cls.BASH, cls.SH, cls.ZSH],
            "mac": [cls.BASH, cls.ZSH, cls.FISH],
            "wsl": [cls.BASH, cls.SH, cls.ZSH],
        }

    def get_shell_command(self) -> str:
        if self == ShellType.BASH:
            return "bash -c"
        if self == ShellType.SH:
            return "sh -c"
        if self == ShellType.BAT:
            return "cmd.exe /c"
        if self == ShellType.CMD:
            return "cmd.exe /c"
        if self == ShellType.POWERSHELL:
            return "powershell.exe -Command"
        if self == ShellType.ZSH:
            return "zsh -c"
        if self == ShellType.FISH:
            return "fish -c"


class CommandExecution(BaseConfigModel):
    run: str
    args: Optional[List[str]] = None
    fail_on_error: bool = False
    valid_exit_codes: Optional[List[int]] = None
    saved_output_name: Optional[str] = None
    elevate: bool = False

    @model_validator(mode="before")
    def set_default_key(cls, values):
        if isinstance(values, str):
            return {"run": values}
        return values

    def create_command(self, shell_command) -> str:
        """Creates a command string from the execute and args fields."""

        cmd = self.run  # Variable substitution happens automatically

        if isinstance(cmd, str) and "\n" in cmd:
            if platform.system().lower() == "linux":
                cmd = "\n".join(
                    f"sudo {line}" if self.elevate else line for line in cmd.split("\n")
                )
                return cmd

        if self.elevate:
            if platform.system().lower() == "linux":
                cmd = f"sudo {cmd}"

        if self.args:
            cmd += " " + " ".join(
                self.args
            )  # Variable substitution happens automatically
        cmd = f'{shell_command} "{cmd}"'
        return cmd

    def save_output(self, output: Any) -> None:
        """Save command output if saved_output_name is specified"""
        if self.saved_output_name:
            store = OutputStore.get_instance()
            store.set_output(self.saved_output_name, output)


class Command(BaseConfigModel):
    shell: ShellType
    os_dist: Optional[str] = None
    execute: Union[CommandExecution, List[CommandExecution]]
    resources: Optional[GroupedResources] = None

    def validate_shell_type(self, os_type: OSType) -> List[ShellType]:
        """Validates package managers against current OS and returns list of valid ones."""
        os_shell_types = ShellType.get_os_shell_types()
        valid_shell_types = []

        for os_name, is_active in os_type.model_dump().items():
            if is_active and os_name in os_shell_types:
                valid_shell_types.extend(os_shell_types[os_name])

        invalid_shell_types = [sh for sh in [self.shell] if sh not in valid_shell_types]
        if invalid_shell_types:
            logger.warning(
                f"Found incompatible shell types for current OS: {invalid_shell_types}"
            )

        return [sh for sh in [self.shell] if sh in valid_shell_types]


class CommandGroup(BaseConfigModel):
    commands: List[Command]
    execution_order: ExecutionOrder = ExecutionOrder.AFTER


class CommandModel(RootModel):
    root: Optional[Dict[str, Union[List[Command], CommandGroup]]] = None

    @model_validator(mode="before")
    def convert_legacy_format(cls, values):
        if not values or not isinstance(values, dict):
            return values

        result = {}
        for group_name, group in values.items():
            if isinstance(group, list):
                # Convert list format to CommandGroup
                result[group_name] = {
                    "commands": group,
                    "execution_order": ExecutionOrder.AFTER,
                }
            else:
                result[group_name] = group
        return result

    def run(self, phase: ExecutionOrder = ExecutionOrder.AFTER):
        import modules.command.command as command_module

        if not self.root:
            return

        for group_name, group in self.root.items():
            if group.execution_order == phase:
                command_module.run_commands(group_name, group.commands)
