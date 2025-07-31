from typing import Optional
from models.shared import SharedModel


class VisualStudio(SharedModel):
    model: Optional[str] = "Visual Studio"

    def execute(self):
        """Execute visual-studio-specific operations"""
        import modules.configure.visual_studio as visual_studio_module

        visual_studio_module.run_visual_studio(self)
