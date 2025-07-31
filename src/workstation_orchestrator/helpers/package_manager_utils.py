from typing import List
from models.base.package_manager import PackageManagerType, get_package_manager
from helpers.helper import get_host_os, get_linux_os_dist
from logger.logger import logger


def get_valid_package_managers_for_os(
    package_managers: List[PackageManagerType], os_config
) -> List[PackageManagerType]:
    """Filter package managers that are valid for the given OS."""
    os_pkg_managers = PackageManagerType.get_os_package_managers()
    valid_pkg_managers = []

    for os_name, is_active in os_config.model_dump().items():
        if is_active and os_name in os_pkg_managers:
            if os_name == "linux":
                # validate linux os for supported package managers - APT, BREW, SNAP, FLATPAK, DNF, YUM
                linux_dist = get_linux_os_dist()
                linux_pkg_managers = []
                if linux_dist in ["ubuntu", "debian", "linuxmint", "pop"]:
                    linux_pkg_managers.append(PackageManagerType.APT)
                elif linux_dist in ["fedora", "rocky", "almalinux"]:
                    linux_pkg_managers.append(PackageManagerType.DNF)
                    linux_pkg_managers.append(PackageManagerType.YUM)
                elif linux_dist in ["centos", "rhel", "oracle"]:
                    linux_pkg_managers.append(PackageManagerType.YUM)
                    linux_pkg_managers.append(PackageManagerType.DNF)

                # Add universal Linux package managers
                linux_pkg_managers.extend(
                    [
                        PackageManagerType.SNAP,
                        PackageManagerType.FLATPAK,
                        PackageManagerType.BREW,  # Homebrew can work on Linux too
                    ]
                )
                valid_pkg_managers.extend(linux_pkg_managers)
            else:
                valid_pkg_managers.extend(os_pkg_managers[os_name])

    # Filter configured package managers to only those valid for this OS
    result = [pm for pm in package_managers if pm in valid_pkg_managers]

    # Log any invalid package managers
    invalid_pkg_managers = [
        pm for pm in package_managers if pm not in valid_pkg_managers
    ]
    if invalid_pkg_managers:
        logger.warning(
            f"Found incompatible package managers for current OS: {invalid_pkg_managers}"
        )

    return result


def get_available_package_managers() -> List[PackageManagerType]:
    """
    Returns a list of available package managers on the system.
    The first package manager in the list is considered the default/preferred one.
    """
    available = []
    selected_package_managers = []
    os = get_host_os()

    # Get list of package managers for current OS
    os_pkg_managers = PackageManagerType.get_os_package_managers()
    for os_name, is_active in os.model_dump().items():

        if is_active and os_name in os_pkg_managers:
            # Try each package manager
            if os_name == "linux":
                # validate linux os for supported package managers - APT, BREW, SNAP, FLATPAK, DNF, YUM
                linux_dist = get_linux_os_dist()
                linux_pkg_managers = []
                for pm_select_type in os_pkg_managers[os_name]:
                    manager = get_package_manager(pm_select_type)
                    if manager is not None:

                        if (
                            linux_dist in ["ubuntu", "debian", "linuxmint", "pop"]
                            and manager.type == PackageManagerType.APT
                        ):
                            linux_pkg_managers.append(PackageManagerType.APT)
                        elif (
                            linux_dist in ["fedora", "rocky", "almalinux"]
                            and manager.type == PackageManagerType.DNF
                        ):
                            linux_pkg_managers.append(PackageManagerType.DNF)
                        elif (
                            linux_dist in ["fedora", "rocky", "almalinux"]
                            and manager.type == PackageManagerType.YUM
                        ):
                            linux_pkg_managers.append(PackageManagerType.YUM)
                        elif (
                            linux_dist in ["centos", "rhel", "oracle"]
                            and manager.type == PackageManagerType.YUM
                        ):
                            linux_pkg_managers.append(PackageManagerType.YUM)
                        elif (
                            linux_dist in ["centos", "rhel", "oracle"]
                            and manager.type == PackageManagerType.DNF
                        ):
                            linux_pkg_managers.append(PackageManagerType.DNF)
                            # # Add universal Linux package managers
                            # linux_pkg_managers.extend(
                            #     [
                            #         PackageManagerType.SNAP,
                            #         PackageManagerType.FLATPAK,
                            #         PackageManagerType.BREW,  # Homebrew can work on Linux too
                            #     ]
                            # )

                            # Only add universal package managers if they're actually installed
                        elif manager.type in [
                            PackageManagerType.SNAP,
                            PackageManagerType.FLATPAK,
                            PackageManagerType.BREW,
                        ]:
                            linux_pkg_managers.append(manager.type)
                selected_package_managers.extend(linux_pkg_managers)
            else:
                selected_package_managers.extend(os_pkg_managers[os_name])

            for pm_type in selected_package_managers:
                manager = get_package_manager(pm_type)
                if manager is not None:
                    available.append(pm_type)
    return available


def get_default_package_manager():
    """
    Returns the default package manager instance for the current system.
    Raises ValueError if no package manager is available.
    """
    available = get_available_package_managers()
    if not available:
        raise ValueError(f"No package manager found for OS: {get_host_os()}")

    return available[-1]
