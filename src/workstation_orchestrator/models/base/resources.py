from typing import List
from models.base_model import BaseConfigModel


class DownloadResource(BaseConfigModel):
    url: str
    path: str


class GroupedResources(BaseConfigModel):
    resources: List[DownloadResource]

    def execute(self):
        """Execute resource-specific operations"""
        import modules.resource.resource as resource_module
        resource_module.run_resource(self)
