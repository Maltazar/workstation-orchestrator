from typing import Dict, Any, Optional, ClassVar, Union
from pydantic import BaseModel
import re
import yaml
import json
from pathlib import Path
import os


class OutputStore(BaseModel):
    """Global store for command outputs and other shared data

    Examples:
        >>> store = OutputStore.get_instance()
        >>> store.set_output("my_var", "hello")
        >>> store.substitute_values("echo ${my_var}")  # Will substitute
        'echo hello'
        >>> store.substitute_values("echo ${PATH}")     # Won't substitute (not in store)
        'echo ${PATH}'
        >>> store.substitute_values("echo ${unknown}")  # Won't substitute (not in store)
        'echo ${unknown}'
    """

    _instance: ClassVar[Optional["OutputStore"]] = None
    outputs: Dict[str, Any] = {}
    _active_os: ClassVar[Optional[str]] = None

    # Add this class variable outside of model fields
    _global_outputs: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "OutputStore":
        """Class method - operates on the class itself
        - Can access cls._instance
        - Can create new instances with cls()
        - Called as OutputStore.get_instance()
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_output(self, key: str, value: Any) -> None:
        """Instance method - operates on specific instances
        - Can access self.outputs
        - Called as instance.set_output()
        """
        if value.endswith("\n"):
            value = value.rstrip("\n")
        self.outputs[key] = value

    def get_output(self, key: str, default: Any = None) -> Any:
        """Instance method - operates on specific instances
        - Can access self.outputs
        - Called as instance.get_output()
        """
        return self.outputs.get(key, default)

    def substitute_values(self, text: str) -> str:
        """Replace all ${variable} and $variable patterns in text with their stored values or environment variables.
        Escaped patterns ($$VAR or $VAR) will not be replaced."""
        if not isinstance(text, str):
            return text

        # Replace escaped $$ with a temporary placeholder
        text = text.replace("$$", "\x00")
        # Replace escaped \$ with a temporary placeholder
        text = text.replace(r"\$", "\x01")

        # Handle ${VAR} syntax
        for match in re.finditer(r"\${(\w+)}", text):
            key = match.group(1)
            if key in self.outputs:
                value = self.outputs[key]
                text = text.replace(f"${{{key}}}", str(value))
            elif key in os.environ:
                text = text.replace(f"${{{key}}}", os.environ[key])

        # Handle $VAR syntax
        for match in re.finditer(r"\$(\w+)", text):
            key = match.group(1)
            if key in self.outputs:
                value = self.outputs[key]
                text = text.replace(f"${key}", str(value))
            elif key in os.environ:
                text = text.replace(f"${key}", os.environ[key])

        # Restore escaped characters
        text = text.replace("\x00", "$")
        text = text.replace("\x01", "$")

        return text

    def load_file(self, path: Union[str, Path]) -> str:
        """Load a file and substitute any variables"""
        path = Path(path)
        content = path.read_text()
        return self.substitute_values(content)

    def load_yaml(self, path: Union[str, Path]) -> dict:
        """Load a YAML file and substitute any variables before parsing"""
        content = self.load_file(path)
        return yaml.safe_load(content)

    def load_json(self, path: Union[str, Path]) -> dict:
        """Load a JSON file and substitute any variables before parsing"""
        content = self.load_file(path)
        return json.loads(content)

    def substitute_dict(self, data: dict) -> dict:
        """Recursively substitute variables in a dictionary"""
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.substitute_dict(value)
            elif isinstance(value, list):
                result[key] = [self.substitute_values(item) for item in value]
            elif isinstance(value, str):
                result[key] = self.substitute_values(value)
            else:
                result[key] = value
        return result

    def clear(self) -> None:
        """Clear all stored outputs"""
        self.outputs.clear()

    def set_active_os(self, os_name: str):
        """Sets the active OS in the global store"""
        self.__class__._active_os = os_name

    def get_active_os(self) -> str:
        """Gets the active OS from the global store"""
        return self.__class__._active_os

    def set_global_output(self, key: str, value: Any) -> None:
        """Sets a global output"""
        self.__class__._global_outputs[key] = value

    def get_global_output(self, key: str, default: Any = None) -> Any:
        """Gets a global output"""
        return self.__class__._global_outputs.get(key, default)
