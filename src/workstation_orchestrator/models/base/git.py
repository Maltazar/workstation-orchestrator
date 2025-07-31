from typing import Dict, List, Optional
from pydantic import Field, model_validator
from models.shared import SharedModel
from models.base_model import BaseConfigModel


class GitGeneralItems(BaseConfigModel):
    root_path: Optional[str] = None
    repo_file_list: Optional[str] = None
    repo_file_type: Optional[str] = None
    repo_file_delimiter: Optional[str] = ","
    repo_file_group_header: Optional[str] = None
    repo_file_repo_header: Optional[str] = None
    repo_file_path_header: Optional[str] = None


class GitRepoItem(GitGeneralItems):
    url: str
    path: Optional[str] = None


class GitRepoGroup(GitGeneralItems):
    enabled: Optional[bool] = True
    use_automated_path: Optional[bool] = False
    no_group_name: Optional[bool] = False
    pull: Optional[bool] = False
    items: Dict[str, List[GitRepoItem]] = None

    @model_validator(mode="before")
    def set_default_key(cls, values):
        items = values.get("items")
        if isinstance(items, list):
            values["no_group_name"] = True
            values["items"] = {"default": items}

        if values.get("items"):
            for group, repos in values["items"].items():
                converted_repos = []
                for repo in repos:
                    if isinstance(repo, str):
                        converted_repos.append({"url": repo})
                    else:
                        converted_repos.append(repo)
                values["items"][group] = converted_repos

        return values


class GitConfig(BaseConfigModel):
    diff_tool: Optional[str] = Field(alias="diff-tool", default=None)
    display_name: Optional[str] = Field(alias="display-name", default=None)
    email: Optional[str] = None
    system_config: Optional[dict[str, list]] = None
    global_config: Optional[dict[str, list]] = None

    @model_validator(mode="before")
    def set_default_key(cls, values):
        # handle single default list values
        if isinstance(values, list):
            values["global_config"] = {"global": values}
            return values

        # handle aliases
        if "system" in values:
            values["system_config"] = values.pop("system")
        if "system-config" in values:
            values["system_config"] = values.pop("system-config")
        if "global" in values:
            values["global_config"] = values.pop("global")
        if "global-config" in values:
            values["global_config"] = values.pop("global-config")

        # handle lists of system config
        if isinstance(values.get("system_config"), list):
            values["system_config"] = {"system": values.pop("system_config")}
        if isinstance(values.get("system-config"), list):
            values["system_config"] = {"system": values.pop("system-config")}
        if isinstance(values.get("system"), list):
            values["system_config"] = {"system": values.pop("system")}

        # handle lists of global config
        if isinstance(values.get("global_config"), list):
            values["global_config"] = {"global": values.pop("global_config")}
        if isinstance(values.get("global-config"), list):
            values["global_config"] = {"global": values.pop("global-config")}
        if isinstance(values.get("global"), list):
            values["global_config"] = {"global": values.pop("global")}

        return values


class GitModel(SharedModel):
    config: Optional[GitConfig] = None
    repos: Optional[Dict[str, GitRepoGroup]] = Field(default_factory=dict)
    pull: Optional[bool] = False

    def execute(self):
        """Execute git-specific operations"""
        import modules.git.git as git_module

        git_module.run_git(self)
