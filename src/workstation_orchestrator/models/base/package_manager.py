from enum import Enum
from typing import Dict, List, Optional, Type, Tuple
from logger.logger import logger
from models.base.os_type import OSType
from helpers.subprocess_helper import run_subprocess


class PackageManagerType(str, Enum):
    """Enum representing different types of package managers"""

    APT = "apt"
    BREW = "brew"
    CHOCO = "choco"
    WINGET = "winget"
    SNAP = "snap"
    FLATPAK = "flatpak"
    DNF = "dnf"
    YUM = "yum"
    PORT = "port"

    @classmethod
    def get_os_package_managers(cls) -> Dict[str, List["PackageManagerType"]]:
        return {
            "windows": [cls.CHOCO, cls.WINGET],
            "linux": [cls.APT, cls.BREW, cls.SNAP, cls.FLATPAK, cls.DNF, cls.YUM],
            "mac": [cls.BREW, cls.PORT],
            "wsl": [cls.APT, cls.BREW, cls.SNAP, cls.FLATPAK, cls.DNF, cls.YUM],
        }


# Cache for package manager availability, keyed by (os_type, package_manager)
_package_manager_cache: Dict[Tuple[str, PackageManagerType], bool] = {}


class BasePackageManager:
    """Base class for package manager implementations"""

    def __init__(self, manager_type: PackageManagerType):
        self.type = manager_type

    def get_install_command(self, package_name: str) -> list[str]:
        """Get the install command for this package manager"""
        raise NotImplementedError("Subclasses must implement get_install_command")

    def get_uninstall_command(self, package_name: str) -> list[str]:
        """Get the uninstall command for this package manager"""
        raise NotImplementedError("Subclasses must implement get_uninstall_command")

    def is_valid_for_os(self, os_type: str) -> bool:
        """Check if this package manager is valid for the given OS type"""
        valid_pms = PackageManagerType.get_os_package_managers().get(os_type, [])
        return self.type in valid_pms

    def is_installed(self, target_os: Optional[OSType] = None) -> bool:
        """
        Check if this package manager is installed and valid for use.

        Args:
            target_os: The target OS from configuration. If provided, validates the
                      package manager is appropriate for that OS.
        """
        from helpers.helper import get_host_os

        # Get current OS
        host_os = get_host_os()
        host_os_type = next((k for k, v in host_os.model_dump().items() if v), None)
        if not host_os_type:
            return False

        # If target OS is provided, check if package manager is valid for it
        if target_os:
            target_os_type = next(
                (k for k, v in target_os.model_dump().items() if v), None
            )
            if not target_os_type or not self.is_valid_for_os(target_os_type):
                logger.debug(
                    f"Package manager {self.type} is not valid for target OS {target_os_type}"
                )
                return False

        # Check if package manager is valid for host OS
        if not self.is_valid_for_os(host_os_type):
            logger.debug(
                f"Package manager {self.type} is not valid for host OS {host_os_type}"
            )
            return False

        # Check cache first using OS-specific key
        cache_key = (host_os_type, self.type)
        if cache_key in _package_manager_cache:
            return _package_manager_cache[cache_key]

        # If not in cache, check system
        from helpers.helper import run_subprocess

        check_cmd = (
            "where.exe"
            if self.type in [PackageManagerType.CHOCO, PackageManagerType.WINGET]
            else "which"
        )
        result = run_subprocess(f"{check_cmd} {self.type.value}")
        is_installed = result.returncode == 0

        # Cache the result
        _package_manager_cache[cache_key] = is_installed
        return is_installed


class AptPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.APT)

    def get_update_command(self) -> list[str]:
        return "apt-get update"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"apt-get install -y {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"apt-get remove -y {package_name}"


class BrewPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.BREW)

    def get_update_command(self) -> list[str]:
        return "brew update"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"brew install --quiet {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"brew uninstall {package_name}"


class ChocolateyPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.CHOCO)

    def get_update_command(self) -> list[str]:
        return "choco upgrade --yes"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"choco install --yes {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"choco uninstall --yes {package_name}"


class WingetPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.WINGET)

    def get_update_command(self) -> list[str]:
        return "winget upgrade --silent"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"winget install --silent {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"winget uninstall --silent {package_name}"


class SnapPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.SNAP)

    def get_update_command(self) -> list[str]:
        return "snap refresh"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"snap install {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"snap remove {package_name}"


class FlatpakPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.FLATPAK)

    def get_update_command(self) -> list[str]:
        return "flatpak update -y"

    def get_install_command(self, package_name: str) -> list[str]:
        # First search for the package
        search_result = run_subprocess(
            f"flatpak search --columns=application {package_name}"
        )
        if search_result.returncode == 0 and search_result.stdout.strip():
            # Get the first match (application ID)
            app_id = search_result.stdout.strip().split("\n")[0]
            logger.debug(f"Found app ID: {app_id}")
            return f"flatpak install -y flathub {app_id}"

        # Fallback to direct install if search fails
        logger.debug(
            f"Failed to find app ID for {package_name}, falling back to direct install"
        )
        return f"flatpak install -y flathub {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"flatpak uninstall -y {package_name}"


class DnfPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.DNF)

    def get_update_command(self) -> list[str]:
        return "dnf update -y"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"dnf install -y {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"dnf remove -y {package_name}"


class YumPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.YUM)

    def get_update_command(self) -> list[str]:
        return "yum update -y"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"yum install -y {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"yum remove -y {package_name}"


class MacPortsPackageManager(BasePackageManager):
    def __init__(self):
        super().__init__(PackageManagerType.PORT)

    def get_update_command(self) -> list[str]:
        return "port selfupdate"

    def get_install_command(self, package_name: str) -> list[str]:
        return f"port install {package_name}"

    def get_uninstall_command(self, package_name: str) -> list[str]:
        return f"port uninstall {package_name}"


# Registry of package manager implementations
PACKAGE_MANAGER_REGISTRY: Dict[PackageManagerType, Type[BasePackageManager]] = {
    PackageManagerType.APT: AptPackageManager,
    PackageManagerType.BREW: BrewPackageManager,
    PackageManagerType.CHOCO: ChocolateyPackageManager,
    PackageManagerType.WINGET: WingetPackageManager,
    PackageManagerType.SNAP: SnapPackageManager,
    PackageManagerType.FLATPAK: FlatpakPackageManager,
    PackageManagerType.DNF: DnfPackageManager,
    PackageManagerType.YUM: YumPackageManager,
    PackageManagerType.PORT: MacPortsPackageManager,
}


def get_package_manager(
    manager_type: PackageManagerType,
    target_os: Optional[OSType] = None,
) -> Optional[BasePackageManager]:
    """
    Factory function to get a package manager instance by type

    Args:
        manager_type: The type of package manager to get
        target_os: The target OS from configuration. If provided, validates the
                  package manager is appropriate for that OS.
    """
    manager_class = PACKAGE_MANAGER_REGISTRY.get(manager_type)
    if not manager_class:
        logger.error(
            f"No implementation found for package manager type: {manager_type}"
        )
        return None

    manager = manager_class()
    # if not manager.is_installed(target_os):
    #     logger.debug(
    #         f"Package manager {manager_type} is not installed or not valid for target OS"
    #     )
    #     return None

    return manager
