from typing import Optional, ClassVar
from pydantic import model_validator
from models.shared_main import SharedMain
from models.os.windows import WindowsModel
from models.os.linux import LinuxModel
from models.os.mac import MacModel
from models.config_processor import deep_merge_dicts
from models.base.command import ShellType
from models.base.os_type import OSType
from pathlib import Path
from collections import OrderedDict
import yaml
import json
from models.base.output_store import OutputStore


class Configuration(SharedMain):
    _current_instance: ClassVar[Optional["Configuration"]] = None
    os: OSType

    # OS-specific configurations
    windows: Optional[WindowsModel] = None
    linux: Optional[LinuxModel] = None
    mac: Optional[MacModel] = None
    wsl: Optional[LinuxModel] = None

    @classmethod
    def get_current(cls) -> "Configuration":
        """Returns the current Configuration instance."""
        if cls._current_instance is None:
            raise RuntimeError("No Configuration instance has been created yet")
        return cls._current_instance

    def __init__(self, **data):
        super().__init__(**data)
        Configuration._current_instance = self

    def get_active_os_config(self) -> OSType:
        """Returns an OSType object for the currently active OS."""
        if not self.get_active_os():
            raise RuntimeError("No active OS set. This is likely a programming error.")
        return OSType(**{self.get_active_os(): True})

    def get_target_os(self) -> list[str]:
        """Returns a list of active OS names."""
        active_os = []
        for os_name in OSType.model_fields.keys():
            if getattr(self.os, os_name):
                active_os.append(os_name)
        return active_os if active_os else ["none"]

    def set_target_os(self, os_name: str) -> None:
        """
        Sets the target OS flag to the specified OS name.
        If the OS name is not recognized, it will be ignored.
        """
        if os_name in OSType.model_fields:
            self.os = OSType(**{os_name: True})

    @model_validator(mode="before")
    def ensure_prepare_section(cls, values):
        """Ensure prepare section exists even if not explicitly defined"""
        if "prepare" not in values or values["prepare"] is None:
            values["prepare"] = {}
        return values

    def merge_os_specific_configs(self, exclude: list[str] = []) -> "Configuration":
        """
        Merges all active OS-specific configurations with the base configuration.
        The order of precedence is: base < first active OS < second active OS, etc.
        """
        os_types = set(OSType.model_fields.keys())
        os_types.add("os")
        os_types.update(exclude)
        # Get the base configuration as a dictionary, excluding None values
        global_config = self.model_dump(
            exclude=os_types, by_alias=True, exclude_none=True, exclude_unset=True
        )

        config_data = {}
        target_os = self.get_target_os()
        other_excludes = set()
        if len(exclude) > 0:
            for exclude_item in exclude:
                for os_name in OSType.model_fields.keys():
                    other_excludes.add(f"{os_name}.{exclude_item}")
            other_excludes.update(exclude)

        for os_name in target_os:
            os_config = getattr(self, os_name)
            os_dict = {}
            if os_config:
                os_dict = os_config.model_dump(
                    exclude=other_excludes,
                    exclude_unset=True,
                    exclude_none=True,
                    by_alias=True,
                )
            merged_dict = deep_merge_dicts(global_config, os_dict)
            config_data[os_name] = merged_dict

        # Create a new Configuration with merged data
        return Configuration(os=self.os, **config_data)

    def dump_yaml(self, output_path: Optional[Path] = None) -> str:
        """Dump the merged configuration to YAML string or file."""
        yaml.add_representer(
            ShellType, lambda dumper, data: dumper.represent_str(data.value)
        )
        merged_config = self.merge_os_specific_configs()
        merged_json = merged_config.model_dump_json(
            by_alias=True, exclude_none=True, exclude_unset=True, indent=2
        )

        yaml_str = yaml.dump(
            json.loads(merged_json),
            default_flow_style=False,
            sort_keys=False,
        )

        if output_path:
            output_path.write_text(yaml_str)

        return yaml_str

    def dump_json(self, output_path: Optional[Path] = None) -> str:
        """Dump the merged configuration to JSON string or file."""
        merged_config = self.merge_os_specific_configs()
        json_str = merged_config.model_dump_json(
            by_alias=True, exclude_none=True, exclude_unset=True, indent=2
        )

        if output_path:
            output_path.write_text(json_str)

        return json_str

    def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
        class OrderedLoader(Loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
        )
        return yaml.load(stream, OrderedLoader)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Configuration":
        """Creates a Configuration instance from YAML content with variable substitution"""
        store = OutputStore.get_instance()
        # First substitute any variables in the raw YAML
        yaml_content = store.substitute_values(yaml_content)
        data = yaml.safe_load(yaml_content)
        # Then substitute in the parsed data
        data = store.substitute_dict(data)
        config = cls(**data)
        return config

    def merge(self, other: "Configuration") -> "Configuration":
        """
        Merge this Configuration with another Configuration instance.
        The other Configuration takes precedence in case of conflicts.
        """
        # First merge the OS flags
        merged_os = self.os.merge(other.os)

        # Get the base configurations as dictionaries
        self_dict = self.model_dump(
            exclude={"os"}, by_alias=True, exclude_none=True, exclude_unset=True
        )
        other_dict = other.model_dump(
            exclude={"os"}, by_alias=True, exclude_none=True, exclude_unset=True
        )

        # Merge the dictionaries using deep_merge_dicts
        merged_dict = deep_merge_dicts(self_dict, other_dict)

        # Create a new Configuration with merged data
        return Configuration(os=merged_os, **merged_dict)
