from typing import Optional
from models.base.command import CommandModel
from models.base_model import BaseConfigModel, ExecutionOrder
from models.base.resources import GroupedResources


class SharedModel(BaseConfigModel):
    """Base configuration that's shared across root and individual models"""

    command: Optional[CommandModel] = None
    resources: Optional[GroupedResources] = None

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
