import platform
from models.base.software import SoftwareModel
from models.config import Configuration
from logger.logger import logger
from helpers.subprocess_helper import run_subprocess
from models.base.package_manager import get_package_manager
from helpers.install_managers import install_package_manager
from helpers.package_manager_utils import (
    get_available_package_managers,
    get_valid_package_managers_for_os,
)


def run_software(software: SoftwareModel):
    """
    Run software installation/uninstallation based on configuration
    """
    logger.info("Running software")

    config = Configuration.get_current()
    os_config = config.get_active_os_config()

    # First validate package managers against current OS
    valid_package_managers = get_valid_package_managers_for_os(
        software.package_managers, os_config
    )
    if not valid_package_managers:
        logger.error(
            f"No valid package managers configured for {config.get_active_os()}"
        )
        return

    # Then get available (installed) package managers from the valid ones
    available_package_managers = get_available_package_managers()
    available_package_managers = [
        pm for pm in available_package_managers if pm in valid_package_managers
    ]
    if not available_package_managers:
        logger.error(
            f"None of the configured package managers ({', '.join(pm.value for pm in software.package_managers)}) are available/installed on OS selected: {config.get_active_os()} for current OS {platform.system().lower()}"
        )
        return

    # Create a map of package manager instances to avoid repeated checks
    package_manager_instances = {}
    for pm_type in available_package_managers:
        pm = get_package_manager(pm_type, os_config)
        if pm:
            package_manager_instances[pm_type] = pm

    # Install packages for each available package manager
    for package_manager in available_package_managers:
        pm = package_manager_instances[package_manager]
        logger.info(f"Running - {package_manager}")
        if not pm.is_installed():
            logger.info(f"Installing {package_manager}")
            install_package_manager(package_manager)

        # Get the package manager configuration
        pm_config = getattr(software, package_manager.value, None)
        if not pm_config:
            continue

        update_cmd = pm.get_update_command()
        logger.info(f"Updating {package_manager} using {update_cmd}")
        result = run_subprocess(update_cmd)
        if result.returncode != 0:
            if "snap" in package_manager.value:
                logger.warning("SNAP can't run in containers")
                logger.warning("this is because systemd is missing for snapd to start")
                logger.warning(f"Failed to update {package_manager}: {result.stderr}")

            else:
                logger.error(
                    f"Failed to update {package_manager}: stderr - {result.stderr} and stdout - {result.stdout}"
                )
            continue

        # Install packages
        for package in pm_config.install:
            package_name = package.name if hasattr(package, "name") else package
            cmd = pm.get_install_command(package_name)

            # Add any additional arguments if specified
            if hasattr(package, "args") and package.args:
                cmd.extend(package.args.split())

            logger.info(f"Installing {package_name} using {package_manager}")
            result = run_subprocess(cmd)

            if result.returncode == 0:
                logger.success(f"Successfully installed {package_name}")
            else:
                logger.error(f"Failed to install {package_name}: {result.stderr}")
