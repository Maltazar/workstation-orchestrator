import os
from pathlib import Path
from typing import List, Union
from models.base.git import GitModel, GitRepoItem, GitRepoGroup
from logger.logger import logger
from helpers.helper import run_subprocess
from helpers.package_manager_utils import get_default_package_manager
from modules.git.git_config import git_config


def git_manual_repo_clones(items: List[GitRepoItem], pull: bool = False):
    for item in items:
        if item.repo_file_list:
            git_use_file_list(item, "")
            continue
        url = git_set_url(item.url)
        if item.root_path:
            path = os.path.join(item.root_path, item.path)
        else:
            path = item.path
        path = git_set_local_path(path)
        git_clone_repo(url, path, pull)


def git_automate_repo_clones(group: GitRepoGroup, pull: bool = False):
    logger.info("Automate Path")
    for name, items in group.items.items():
        for item in items:
            if item.repo_file_list:
                git_use_file_list(item, name)
                continue
            url = git_set_url(item.url)
            path = ""
            if group.no_group_name:
                logger.debug(f"No group name for {name}")
                logger.debug(f"Using root path: {group.root_path}")
                logger.debug(f"Using url: {url}")
                path = git_get_automate_path(url, group.root_path, "")
            else:
                logger.debug(f"Group name for {name}")
                logger.debug(f"Using root path: {group.root_path}")
                logger.debug(f"Using url: {url}")
                path = git_get_automate_path(url, group.root_path, name)
            path = git_set_local_path(path)
            git_clone_repo(url, path, pull)


def git_get_automate_path(url: str, root_path: str, group_name: str = "") -> str:
    if url.startswith("git@"):
        domain, path = url.split(":")
        domain = domain.replace("git@", "")
    elif url.startswith("ssh://"):
        domain, path = url.split(":", 1)
        domain = domain.replace("ssh://", "")
    else:
        # Remove credentials from the URL
        if "@" in url:
            url = url.split("@")[-1]
        else:
            url = url.replace("https://", "").replace("http://", "")
        domain, path = url.split("/", 1)

    logger.debug(f"Path: {path}")
    path_parts = path.replace(".git", "").lower().split("/")
    follow_paths = "/".join(path_parts)

    if group_name:
        formatted_path = os.path.join(
            root_path,
            domain,
            group_name,
            path_parts[0].lower(),
            follow_paths,
        )
    else:
        formatted_path = os.path.join(root_path, domain, follow_paths)

    return formatted_path


def git_set_url(url: str) -> str:
    # logger.warning(f"Not implemented yet: {url} - return as is")
    return url


def git_set_local_path(local_path: str) -> str:
    repo_path = Path(local_path)
    repo_path.mkdir(parents=True, exist_ok=True)
    return local_path


def git_clone_repo(repo_url: str, local_path: str, pull: bool = False) -> Path:
    plain_repo_url = repo_url
    repo_path = Path(local_path)
    if repo_path.exists() and (repo_path / ".git").exists():
        logger.info(f"Repository already exists at {local_path}")
        if pull:
            logger.info(f"Pulling latest changes from {plain_repo_url}")
            run_subprocess(f"git -C {local_path} fetch --quiet")
            status = run_subprocess(f"git -C {local_path} status --short --branch")
            if status.returncode != 0:
                logger.error(f"Command failed: {status}")
                logger.error(status.stderr)
            status = status.stdout.strip()
            if "behind" in status and pull:
                logger.info("Repository is behind. Try to pulling latest changes")
                result = run_subprocess(f"git -C {local_path} pull --quiet")
                if result.returncode != 0:
                    logger.warning(
                        f"Failed to pull latest changes for repository {local_path}"
                    )
                else:
                    logger.success(f"Pulled latest changes to repository {local_path}")
            else:
                logger.info("Repository is up to date")
    else:
        logger.info(f"Cloning repository {plain_repo_url} to {local_path}")
        result = run_subprocess(f"git clone {repo_url} {local_path}")
        if result.returncode != 0:
            logger.warning(
                f"Failed to clone repository {plain_repo_url} to {local_path}"
            )
            logger.warning(result.stderr)
        else:
            logger.success(f"Cloned repository {plain_repo_url} to {local_path}")
    return repo_path


def git_use_file_list(item: Union[GitRepoItem, GitRepoGroup], group_name: str):
    logger.info(f"Using file list {item.repo_file_list}")
    logger.warning(f"Not implemented yet: {item.repo_file_list}")


def git_exists() -> bool:
    result = run_subprocess("git --version")
    return result.returncode == 0


def git_install():
    package_manager = get_default_package_manager()
    result = run_subprocess(f"{package_manager} install git")
    if result.returncode != 0:
        logger.error(f"Command failed: {result}")
        logger.error(result.stderr)
    else:
        logger.success("Git installed successfully")


def run_git(git: GitModel):
    logger.info("Running git")
    pull = git.pull
    if not git_exists():
        git_install()
    else:
        logger.debug("Git already installed")

    for group_name, group in git.repos.items():
        if group.enabled:
            if group.pull:
                pull = group.pull
            logger.info(f"Running git group: {group_name}")
            if group.repo_file_list:
                logger.info("Using file list")
                git_use_file_list(group, "")
            elif group.use_automated_path:
                logger.info(f"Automating path for {group_name}")
                git_automate_repo_clones(group, pull)
            else:
                logger.info(f"Using manual path for {group_name}")
                git_manual_repo_clones(group.items, pull)

    if git.config:
        git_config(git.config)
