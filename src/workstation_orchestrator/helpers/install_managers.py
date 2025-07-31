from helpers.helper import update_shell_config, get_current_shell
from helpers.subprocess_helper import run_subprocess
from logger.logger import logger
from models.base.package_manager import PackageManagerType, BasePackageManager
from helpers.package_manager_utils import (
    get_default_package_manager,
    get_package_manager,
)
import os
import time


def install_package_manager(package_manager: PackageManagerType):
    logger.info(f"install_package_manager {package_manager.value}")
    package_manager = BasePackageManager(package_manager)
    if package_manager.type == PackageManagerType.BREW:
        return install_brew(package_manager)
    elif package_manager.type == PackageManagerType.SNAP:
        return install_snap(package_manager)
    elif package_manager.type == PackageManagerType.FLATPAK:
        return install_flatpak(package_manager)
    elif package_manager.type == PackageManagerType.APT:
        raise NotImplementedError(
            "APT is OS native, can't be installed, validate your config"
        )
    elif package_manager.type == PackageManagerType.CHOCO:
        return install_choco(package_manager)
    elif package_manager.type == PackageManagerType.WINGET:
        return install_winget(package_manager)
    elif package_manager.type == PackageManagerType.DNF:
        raise NotImplementedError(
            "DNF is OS native, can't be installed, validate your config"
        )
    elif package_manager.type == PackageManagerType.YUM:
        raise NotImplementedError(
            "YUM is OS native, can't be installed, validate your config"
        )
    elif package_manager.type == PackageManagerType.PORT:
        raise NotImplementedError(
            "PORT is OS native, can't be installed, validate your config"
        )
    else:
        raise ValueError(f"Unknown package manager: {package_manager.type}")


def install_brew(package_manager: BasePackageManager):
    if package_manager.is_installed():
        logger.info("Homebrew is already installed")
        return True

    # Install required dependencies first
    logger.info("Installing required dependencies for Homebrew")
    default_pm_type = get_default_package_manager()
    default_pm = get_package_manager(default_pm_type)  # Convert type to instance
    if not default_pm:
        logger.error("No default package manager available to install dependencies")
        return False

    # First update package lists
    logger.info("Updating package lists")
    update_result = run_subprocess(default_pm.get_update_command())
    if update_result.returncode != 0:
        logger.error("Failed to update package lists")
        return False

    # Install all required dependencies
    dependencies = {
        PackageManagerType.APT: [
            "build-essential",
            "coreutils",
            "curl",
            "file",
            "git",
            "procps",
        ],
        PackageManagerType.DNF: [
            "gcc",
            "gcc-c++",
            "make",
            "coreutils",
            "curl",
            "file",
            "git",
            "procps-ng",
        ],
        PackageManagerType.YUM: [
            "gcc",
            "gcc-c++",
            "make",
            "coreutils",
            "curl",
            "file",
            "git",
            "procps-ng",
        ],
    }.get(default_pm.type, [])

    if not dependencies:
        logger.warning(
            f"No known dependencies for package manager {default_pm.type.value}"
        )
        return False

    for dep in dependencies:
        result = run_subprocess(default_pm.get_install_command(dep))
        if result.returncode != 0:
            logger.error(f"Failed to install required dependency: {dep}")
            return False

    logger.info("Installing Homebrew")
    url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

    # First try to download the script
    download_result = run_subprocess(f"curl -fsSL {url} -o /tmp/install_homebrew.sh")
    if download_result.returncode != 0:
        logger.error("Failed to download Homebrew installation script")
        logger.error(download_result.stderr)
        return False

    # Make the script executable
    chmod_result = run_subprocess("chmod +x /tmp/install_homebrew.sh")
    if chmod_result.returncode != 0:
        logger.error("Failed to make Homebrew installation script executable")
        logger.error(chmod_result.stderr)
        return False

    # Use detected shell to run the script
    shell_path, _ = get_current_shell()
    if not shell_path:
        logger.error("No valid shell found to run the installation script")
        return False

    # Use interactive mode for the installation
    result = run_subprocess(f"{shell_path} /tmp/install_homebrew.sh", interactive=True)

    if result.returncode != 0:
        logger.error("Failed to install Homebrew")
        return False

    # Clean up
    run_subprocess("rm /tmp/install_homebrew.sh")

    # After successful installation, update shell configuration
    if result.returncode == 0:
        brew_dir = "/home/linuxbrew/.linuxbrew"
        brew_bin = f"{brew_dir}/bin"
        brew_path = f"{brew_bin}/brew"

        # Update current process environment
        os.environ["PATH"] = f"{brew_bin}:{os.environ.get('PATH', '')}"

        # Add to shell config for future sessions
        brew_config = f"""
export PATH={brew_bin}:$PATH
eval "$({brew_path} shellenv)"
"""
        return update_shell_config(brew_config, "Homebrew configuration")

    return False


def install_snap(package_manager: BasePackageManager):
    if package_manager.is_installed():
        logger.info("Snap is already installed")
        return True

    default_pm_type = get_default_package_manager()
    default_pm = get_package_manager(default_pm_type)
    logger.info(f"Installing Snap using {default_pm.type.value}")

    # Use update command from package manager class
    result = run_subprocess(default_pm.get_update_command())
    if result.returncode != 0:
        logger.error(f"Failed to update {default_pm}")
        logger.error(result.stderr)
        return False

    # Use install command from package manager class
    result = run_subprocess(default_pm.get_install_command("snapd"))
    if result.returncode != 0:
        logger.error(f"Failed to install Snap using {default_pm.type.value}")
        logger.error(result.stderr)
        return False

    # Check if we're in a container
    if os.path.exists("/.dockerenv") or os.getenv("container"):
        logger.warning(
            "Container environment detected - snap requires systemd and mount capabilities"
        )
        logger.warning(
            "Snap installation completed but service cannot be started in this container"
        )
        logger.warning(
            "Please use an alternative package manager or run in a VM/native environment"
        )
        return False
    else:
        # Only try service management in non-container environments
        logger.info("Enabling and starting snapd service")
        result = run_subprocess("systemctl enable --now snapd.service")
        if result.returncode != 0:
            logger.error("Failed to enable snapd service")
            logger.error(result.stderr)
            return False

        # Wait for the socket to be available
        logger.info("Waiting for snapd socket to become available")
        for _ in range(10):
            if os.path.exists("/run/snapd.socket"):
                break
            time.sleep(1)
        else:
            logger.error("Timed out waiting for snapd socket")
            return False

    return True


def install_flatpak(package_manager: BasePackageManager):
    if package_manager.is_installed():
        logger.info("Flatpak is already installed")
        return True
    default_pm_type = get_default_package_manager()
    default_pm = get_package_manager(default_pm_type)
    logger.info(f"Installing Flatpak using {default_pm.type.value}")

    # Use update command from package manager class
    result = run_subprocess(default_pm.get_update_command())
    if result.returncode != 0:
        logger.error(f"Failed to update {default_pm.type.value}")
        logger.error(result.stderr)
        return False

    # Use install command from package manager class
    result = run_subprocess(default_pm.get_install_command("flatpak"))
    if result.returncode != 0:
        logger.error(f"Failed to install Flatpak using {default_pm.type.value}")
        logger.error(result.stderr)
        return False

    # Add Flathub repository
    logger.info("Adding Flathub repository")
    result = run_subprocess(
        "flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo"
    )
    if result.returncode != 0:
        logger.error("Failed to add Flathub repository")
        logger.error(result.stderr)
        return False

    return True


def install_choco(package_manager: BasePackageManager):
    if package_manager.is_installed():
        logger.info("Chocolatey is already installed")
        return True
    logger.info("Installing Chocolatey")
    result = run_subprocess(
        "powershell -Command Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    )
    if result.returncode != 0:
        logger.error("Failed to install Chocolatey")
        logger.error(result.stderr)
        return False
    return True


def install_winget(package_manager: BasePackageManager):
    if package_manager.is_installed():
        logger.info("Winget is already installed")
        return True
    logger.info("Installing Winget")
    powershell_script = """
        $progressPreference = 'silentlyContinue'
        Write-Host "Installing WinGet PowerShell module from PSGallery..."
        Install-PackageProvider -Name NuGet -Force | Out-Null
        Install-Module -Name Microsoft.WinGet.Client -Force -Repository PSGallery | Out-Null
        Write-Host "Using Repair-WinGetPackageManager cmdlet to bootstrap WinGet..."
        Repair-WinGetPackageManager
        Write-Host "Done."
    """
    result = run_subprocess(f"powershell -Command {powershell_script}")
    if result.returncode != 0:
        logger.error("Failed to install Winget")
        logger.error(result.stderr)
        return False
    return True
