from typing import List, Optional
from pydantic import Field
from models.base.install import InstallItem
from models.base_model import BaseConfigModel
from models.shared import SharedModel
from models.base.package_manager import PackageManagerType


class SoftwareManager(BaseConfigModel):
    install: List[InstallItem] = Field(default_factory=list)


class SoftwareModel(SharedModel):
    package_managers: List[PackageManagerType] = Field(
        default_factory=list, alias="package-managers"
    )
    apt: Optional[SoftwareManager] = None
    brew: Optional[SoftwareManager] = None
    dnf: Optional[SoftwareManager] = None
    yum: Optional[SoftwareManager] = None
    port: Optional[SoftwareManager] = None
    snap: Optional[SoftwareManager] = None
    flatpak: Optional[SoftwareManager] = None
    choco: Optional[SoftwareManager] = None
    winget: Optional[SoftwareManager] = None

    def execute(self):
        """Execute resource-specific operations"""
        import modules.software.software as software_module

        software_module.run_software(self)
