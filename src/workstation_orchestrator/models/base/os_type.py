from models.base_model import BaseConfigModel


class OSType(BaseConfigModel):
    windows: bool = False
    linux: bool = False
    mac: bool = False
    wsl: bool = False
    unsupported: bool = False

    def merge(self, other: "OSType") -> "OSType":
        """Merge two OSType instances by OR-ing their boolean flags."""
        return OSType(
            windows=self.windows or other.windows,
            linux=self.linux or other.linux,
            mac=self.mac or other.mac,
            wsl=self.wsl or other.wsl,
        )
