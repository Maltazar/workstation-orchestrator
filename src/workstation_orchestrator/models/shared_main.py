from typing import Optional
from pydantic import Field
from models.base.git import GitModel
from models.base.os import OSSettingModel
from models.base.software import SoftwareModel
from models.base.command import CommandModel
from models.configure.config import ConfigureModel
from models.base.prepare import PrepareModel
from models.base_model import BaseConfigModel, ExecutionOrder


class SharedMain(BaseConfigModel):
    """Base configuration that's shared across root and OS-specific configs"""

    command: Optional[CommandModel] = None
    git: Optional[GitModel] = None
    software: Optional[SoftwareModel] = None
    prepare: Optional[PrepareModel] = None
    os_settings: Optional[OSSettingModel] = Field(None, alias="os-settings")
    configure: Optional[ConfigureModel] = None

    def run(self):
        """Main execution flow that handles commands and delegates to model-specific logic"""
        # Run pre-commands
        if self.command:
            self.command.run(ExecutionOrder.BEFORE)
            
        # Run model-specific logic
        self.execute()
            
        # Run post-commands
        if self.command:
            self.command.run(ExecutionOrder.AFTER)
    
    def execute(self):
        """Override this method to implement model-specific logic.
        This will be called between pre and post commands."""
        pass
