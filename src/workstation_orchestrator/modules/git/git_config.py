from models.base.git import GitConfig
from helpers.helper import run_subprocess
from logger.logger import logger
from helpers.helper import get_host_os

allowed_to_fail = [
    "unset-all",
    "unset",
    "remove-section",
    "rename-section",  # might fail if old section doesn't exist
]


def git_config(config: GitConfig):
    logger.info("Running git config")
    if config.display_name:
        git_config_global(f"--replace-all user.name '{config.display_name}'")
    if config.email:
        git_config_global(f"--replace-all user.email '{config.email}'")

    if config.system_config:
        for key, value in config.system_config.items():
            for item in value:
                if key in ["windows", "linux"]:
                    if get_host_os().windows and key == "windows":
                        logger.info(f"Running git config system: {key}")
                        git_config_system(f"{item}")
                    if get_host_os().linux and key == "linux":
                        logger.info(f"Running git config system: {key}")
                        git_config_system(f"{item}")
                else:
                    logger.info(f"Running git config system: {key}")
                    git_config_system(f"{item}")
    if config.global_config:
        for key, value in config.global_config.items():
            for item in value:
                if key in ["windows", "linux"]:
                    if get_host_os().windows and key == "windows":
                        logger.info(f"Running git config global: {key}")
                        git_config_global(f"{item}")
                    if get_host_os().linux and key == "linux":
                        logger.info(f"Running git config global: {key}")
                        git_config_global(f"{item}")
                else:
                    logger.info(f"Running git config global: {key}")
                    git_config_global(f"{item}")

    if config.diff_tool == "vscode":
        logger.info("Setting diff tool to vscode")
        git_set_diff_vscode()
    elif config.diff_tool:
        logger.info(f"Setting diff tool to {config.diff_tool}")
        git_config_global(f"diff.tool {config.diff_tool}")


def git_set_diff_vscode():
    logger.info("Setting diff tool to vscode")
    git_code_name = "difftool.vscode.sh"
    git_code_name_merge = "mergetool.vscode.sh"
    if get_host_os().windows:
        git_code_name = "difftool.vscode.cmd"
        git_code_name_merge = "mergetool.vscode.cmd"

    result = run_subprocess("git config --global diff.tool vscode")
    if result.returncode != 0:
        logger.error("Failed to set diff tool to vscode")
        logger.error(result.stderr)

    cmds = [
        "git config --global diff.tool vscode",
        f'git config --global {git_code_name} "code --wait --diff $LOCAL $REMOTE"',
        "git config --global merge.tool vscode",
        f'git config --global {git_code_name_merge} "code --wait $MERGED"',
    ]

    for cmd in cmds:
        result = run_subprocess(cmd)
        if result.returncode != 0:
            logger.error(f"Failed to run git config: {cmd}")
            logger.error(result.stderr)


def git_config_system(value: str):
    fail_on_error = True
    logger.info(f"Running git config system: {value}")
    result = run_subprocess(f"sudo git config --system {value}")
    for item in allowed_to_fail:
        if item in value:
            fail_on_error = False
    if result.returncode != 0 and fail_on_error:
        logger.error(f"Failed to run git config system: {value}")
        logger.error(result.stderr)
    else:
        logger.success(f"Successfully ran git config system: {value}")


def git_config_global(value: str):
    fail_on_error = True
    logger.info(f"Running git config global - {value}")
    result = run_subprocess(f"git config --global {value}")
    for item in allowed_to_fail:
        if item in value:
            fail_on_error = False
    if result.returncode != 0 and fail_on_error:
        logger.error(f"Failed to run git config global: {value}")
        logger.error(result.stderr)
    else:
        logger.success(f"Successfully ran git config global: {value}")
