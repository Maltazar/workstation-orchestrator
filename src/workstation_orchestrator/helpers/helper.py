from helpers.subprocess_helper import run_subprocess
from models.base.resources import DownloadResource
import requests
import platform
import distro
from pathlib import Path
from models.config import Configuration
from logger.logger import logger
from models.base.os_type import OSType
import os


def download_config(url: str, verify_ssl: bool = True) -> str:
    clean_url = url.split("?")[0]
    filename = clean_url.split("/")[-1]
    resource = DownloadResource(url=url, path=f"downloads/{filename}")
    download_resource(resource, verify_ssl=verify_ssl)
    return resource.path


def download_resource(resource: DownloadResource, verify_ssl: bool = True):
    logger.info(f"Downloading resource: {resource}")
    if verify_ssl:
        validate_global = resource.get_global_output("insecure")
        if validate_global:
            logger.info("Insecure mode enabled")
            verify_ssl = False
    if resource.url:
        if resource.url.startswith("http"):
            response = requests.get(resource.url, verify=verify_ssl)
            if response.status_code == 200:
                logger.success("Resource downloaded successfully")
        else:
            logger.error("Resource URL is not a valid HTTP URL")
            return
    else:
        logger.warning("No resource to download")
        return

    # Create default path if not provided
    if not resource.path:
        resource.path = f"downloads/{resource.url.split('/')[-1]}"

    # Ensure directory exists
    Path(resource.path).parent.mkdir(parents=True, exist_ok=True)

    # Write content to file
    try:
        with open(resource.path, "wb") as f:
            f.write(response.content)
        logger.success(f"Saved to {resource.path}")
    except Exception as e:
        logger.error(f"Failed to save file: {str(e)}")


def merge_yaml(yaml: str, config: Configuration) -> Configuration:
    if not yaml or not Path(yaml).exists():
        logger.error(f"File {yaml} does not exist")
        return config
    with open(yaml, "r") as file:
        yaml_data = file.read()
    yaml_config = Configuration.from_yaml(yaml_data)
    return config.merge(yaml_config)


def get_host_os() -> OSType:
    system = platform.system().lower()
    if system == "windows":
        return OSType(windows=True)
    elif system == "linux":
        return OSType(linux=True)
    elif system == "darwin":
        return OSType(mac=True)
    else:
        logger.error(f"Unsupported operating system: {system}")
        return OSType(unsupported=True)


def get_linux_os_dist() -> str:
    return distro.id().lower()


def is_same_linux_dist(dist: str) -> bool:
    debian_dists = ["ubuntu", "debian", "linuxmint", "pop"]
    fedora_dists = ["fedora", "rocky", "almalinux"]
    centos_dists = ["centos", "rhel", "oracle"]

    if get_linux_os_dist() in debian_dists and dist in debian_dists:
        return True
    elif get_linux_os_dist() in fedora_dists and dist in fedora_dists:
        return True
    elif get_linux_os_dist() in centos_dists and dist in centos_dists:
        return True
    logger.warning(
        f"Unsupported Linux distribution: config: {dist} host: {get_linux_os_dist()}"
    )
    return False


def get_current_shell() -> tuple[str, str]:
    """
    Detects the current shell and its config file path.

    Returns:
        tuple[str, str]: (shell_path, config_file_path) or ("", "") if not detected
    """
    shell_configs = {
        "zsh": "~/.zshrc",
        "bash": "~/.bashrc",
        "/bin/zsh": "~/.zshrc",
        "/bin/bash": "~/.bashrc",
        "/usr/bin/zsh": "~/.zshrc",
        "/usr/bin/bash": "~/.bashrc",
        "sh": "~/.profile",
        "/bin/sh": "~/.profile",
    }

    shell_check = run_subprocess("echo $SHELL")
    current_shell = shell_check.stdout.strip()

    if current_shell in shell_configs:
        return current_shell, shell_configs[current_shell]

    # Fallback to checking available shells
    for shell in ["/bin/bash", "/bin/zsh", "/bin/sh"]:
        if os.path.exists(shell):
            return shell, shell_configs.get(shell, "~/.profile")

    return "", ""


def update_shell_config(config_lines: str, comment: str = "") -> bool:
    """
    Updates shell configuration files with provided configuration lines.

    Args:
        config_lines (str): The configuration lines to add
        comment (str, optional): A comment to add above the configuration

    Returns:
        bool: True if successful, False otherwise
    """
    current_shell, config_file = get_current_shell()

    if not current_shell or not config_file:
        logger.warning("Could not detect shell configuration")
        logger.info("Please manually add the following to your shell configuration:")
        logger.info(config_lines)
        return False

    config_file = os.path.expanduser(config_file)
    logger.info(f"Updating {config_file}")

    # Always check for existing configuration
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            content = f.read()
            if comment in content:
                logger.info(f"Configuration for {comment} already exists")
                return True

    # Prepare the configuration block
    config_block = (
        f"\n# {comment}\n{config_lines.strip()}\n"
        if comment
        else f"\n{config_lines.strip()}\n"
    )

    try:
        with open(config_file, "a") as f:
            f.write(config_block)
        logger.info(f"Updated {config_file} successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to update shell configuration: {e}")
        return False
