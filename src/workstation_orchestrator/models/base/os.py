from models.shared import SharedModel
from typing import Optional
from models.base_model import BaseConfigModel


class TimeFormatConfig(BaseConfigModel):
    shortTime: Optional[str]
    longTime: Optional[str]


class OSSettingModel(SharedModel):
    language: Optional[str]
    region: Optional[str]
    fontSize: Optional[int]
    cursorSpeed: Optional[int]
    notifications: Optional[bool]
    powerProfile: Optional[str]
    timeFormat: Optional[TimeFormatConfig]

    def execute(self):
        """Execute os-settings-specific operations"""
        import modules.os_settings.os_settings as os_settings_module
        os_settings_module.run_os_settings(self)
