from typing import List, Optional
from pydantic import Field
from models.shared_main import SharedMain
from models.base.install import InstallItem
from models.base_model import BaseConfigModel


class WindowsFeatures(BaseConfigModel):
    install: List[InstallItem] = Field(default_factory=list)

    def run(self):
        import modules.os.windows as windows_module

        windows_module.run_windows(self)


class WindowsPowershellModules(BaseConfigModel):
    install: List[InstallItem] = Field(default_factory=list)

    def run(self):
        import modules.os.windows as windows_module

        windows_module.run_windows(self)


class WindowsModel(SharedMain):
    features: Optional[WindowsFeatures] = None
    powershell_modules: Optional[WindowsPowershellModules] = Field(
        alias="powershell-modules", default=None
    )

    def execute(self):
        """Execute windows-specific operations"""
        import modules.os.windows as windows_module

        windows_module.run_windows(self)
