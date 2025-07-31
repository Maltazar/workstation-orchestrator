from pydantic import Field
from typing import Optional
from models.configure.vscode import VSCode
from models.configure.visual_studio import VisualStudio
from models.shared import SharedModel


class ConfigureModel(SharedModel):
    vscode: Optional[VSCode] = None
    visual_studio: Optional[VisualStudio] = Field(alias="visual-studio", default=None)

    def execute(self):
        """Execute configure-specific operations"""
        import modules.configure.configure as configure_module

        configure_module.run_configure(self)
