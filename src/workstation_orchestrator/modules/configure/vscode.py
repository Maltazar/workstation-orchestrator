import json
from pathlib import Path
from models.configure.vscode import VSCode
from logger.logger import logger
from helpers.subprocess_helper import run_subprocess
from typing import Dict
from helpers.helper import download_config, get_host_os
from models.base.os_type import OSType
import os


def get_vscode_settings_path() -> Path:
    """Get the path to VSCode settings.json based on OS."""
    if get_host_os() == OSType.WINDOWS:  # Windows
        settings_path = Path(os.getenv("APPDATA")) / "Code" / "User" / "settings.json"
    else:  # Linux/Mac
        settings_path = Path.home() / ".config" / "Code" / "User" / "settings.json"

    # Create directory if it doesn't exist
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    return settings_path


def read_json_file(file_path: Path) -> Dict:
    """Read and parse JSON file, return empty dict if file doesn't exist."""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in {file_path}, starting fresh")
    return {}


def merge_settings(existing_settings: Dict, new_settings: Dict) -> Dict:
    """Deep merge two settings dictionaries."""
    merged = existing_settings.copy()

    for key, value in new_settings.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_settings(merged[key], value)
        else:
            merged[key] = value

    return merged


def process_vscode_settings(vscode: VSCode) -> None:
    """Process VSCode settings from file or content."""
    settings_path = get_vscode_settings_path()
    existing_settings = read_json_file(settings_path)
    new_settings = {}

    if vscode.settings:
        logger.info("Processing VSCode settings")

        # Handle settings from file
        if vscode.settings.file:
            file_path = Path(vscode.settings.file)
            logger.debug(f"Processing settings file: {file_path}")

            # Download file if it's a URL
            if str(file_path).startswith(("http://", "https://")):
                try:
                    downloaded_path = download_config(str(file_path))
                    file_path = Path(downloaded_path)
                except Exception as e:
                    logger.error(f"Failed to download settings file: {e}")
                    return

            # Read the settings file
            file_settings = read_json_file(file_path)
            new_settings = merge_settings(new_settings, file_settings)

        # Handle settings from content
        if vscode.settings.content:
            logger.debug("Processing settings content")
            try:
                if isinstance(vscode.settings.content, str):
                    content_settings = json.loads(vscode.settings.content)
                else:
                    content_settings = vscode.settings.content
                new_settings = merge_settings(new_settings, content_settings)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings content: {e}")
                return

        # Merge and save the final settings
        if new_settings:
            final_settings = merge_settings(existing_settings, new_settings)
            try:
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(final_settings, f, indent=2)
                logger.success(
                    f"Successfully updated VSCode settings at {settings_path}"
                )
            except Exception as e:
                logger.error(f"Failed to save settings: {e}")


def run_vscode(vscode: VSCode):
    logger.info("Running vscode")
    for command in vscode.extensions.install:
        logger.info(f"Running command: {command}")
        result = run_subprocess(command)
        if result.returncode != 0:
            logger.error(result.stderr)
            logger.error(result.stdout)

    for command in vscode.extensions.uninstall:
        logger.info(f"Running command: {command}")
        result = run_subprocess(command)
        if result.returncode != 0:
            logger.error(result.stderr)
            logger.error(result.stdout)

    logger.success("VSCode extensions installed successfully")

    process_vscode_settings(vscode)
