from typing import Dict, List, Optional
from pydantic import Field
from models.base.resources import GroupedResources
from models.shared import SharedModel
from models.base_model import BaseConfigModel, ExecutionOrder


class MergeYamls(BaseConfigModel):
    enabled: bool = False
    yamls: Optional[List[str]] = None


class PrepareModel(SharedModel):
    download: Optional[Dict[str, GroupedResources]] = Field(default_factory=dict)
    merge_yamls: Optional[Dict[str, MergeYamls]] = Field(
        default_factory=dict, alias="merge-yamls"
    )

    class Config:
        populate_by_name = True

    def run(self, *args, **kwargs):
        """overwrite this method to implement model-specific logic.
        This will be called between pre and post commands."""
        # Run pre-commands
        import modules.prepare.prepare as prepare_module

        if self.command:
            self.command.run(ExecutionOrder.BEFORE)

        # Run model-specific logic
        config = prepare_module.run_prepare(self, *args, **kwargs)

        # Run post-commands
        if self.command:
            self.command.run(ExecutionOrder.AFTER)

        return config
