from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Any, ClassVar, Optional
from models.base.output_store import OutputStore


class ExecutionOrder(Enum):
    BEFORE = "before"
    AFTER = "after"
    TARGET = "target"

    def __str__(self):
        return self.value

    def model_dump(self):
        return self.value


class BaseConfigModel(BaseModel):
    """Base model with common configuration for all models"""

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        populate_by_name=True,
        exclude_unset=True,
        exclude_defaults=True,
        validate_default=True,
    )

    def __getattribute__(self, name: str) -> Any:
        """Override attribute access to substitute variables in string values"""
        value = super().__getattribute__(name)
        if isinstance(value, str):
            store = OutputStore.get_instance()
            return store.substitute_values(value)
        return value

    def model_dump(self, **kwargs):
        """Override model_dump to substitute variables in output"""
        data = super().model_dump(**kwargs)
        store = OutputStore.get_instance()
        return store.substitute_dict(data)

    def get_active_os(self) -> str:
        """Returns the active OS"""
        store = OutputStore.get_instance()
        return store.get_active_os()

    def set_active_os(self, os_name: str):
        """Sets the active OS"""
        store = OutputStore.get_instance()
        store.set_active_os(os_name)

    def set_global_output(self, key: str, value: Any) -> None:
        """Sets a global output"""
        store = OutputStore.get_instance()
        store.set_global_output(key, value)

    def get_global_output(self, key: str, default: Any = None) -> Any:
        """Gets a global output"""
        store = OutputStore.get_instance()
        return store.get_global_output(key, default)
