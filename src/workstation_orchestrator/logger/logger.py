import logging
import os
from colorama import Fore, Style, init
from typing import Optional

# Initialize colorama for cross-platform color support
init()


class ColorFormatter(logging.Formatter):
    """Custom formatter with standard log level colors"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.BLUE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "SUCCESS": Fore.GREEN + Style.BRIGHT,
        "SECTION": Fore.CYAN + Style.BRIGHT,
        "OUTPUT": Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        # Let the parent formatter create asctime first
        formatted = super().format(record)

        # Get the appropriate color for the level
        color = self.COLORS.get(record.levelname, "")

        # Color only the level name, not the whole message
        levelname = f"{color}{record.levelname:^7}{Style.RESET_ALL}"

        # Replace the level name in the formatted string
        return formatted.replace(record.levelname, levelname)


class ColorLogger:
    def __init__(self, name: Optional[str] = None):
        # Create custom success level
        logging.SUCCESS = 25  # Between INFO and WARNING
        logging.addLevelName(logging.SUCCESS, "SUCCESS")
        logging.SECTION = 26  # Between INFO and WARNING
        logging.addLevelName(logging.SECTION, "SECTION")
        logging.OUTPUT = 15  # Between DEBUG and INFO
        logging.addLevelName(logging.OUTPUT, "OUTPUT")

        self.logger = logging.getLogger(name or __name__)

        # Convert string log level to actual logging level
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        self.logger.setLevel(log_level)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Create console handler with custom formatter
            console = logging.StreamHandler()
            # Make sure handler level is also set correctly
            console.setLevel(log_level)
            formatter = ColorFormatter(
                "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            console.setFormatter(formatter)
            self.logger.addHandler(console)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def log_active_config(self, os_name: str):
        self.logger.log(logging.SECTION, f"{os_name.upper()} = Active OS")

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

    def success(self, msg: str):
        self.logger.log(logging.SUCCESS, msg)

    def output(self, msg: str):
        self.logger.log(logging.OUTPUT, msg)

    def is_debug(self):
        return self.logger.isEnabledFor(logging.DEBUG)


# Create default logger instance
logger = ColorLogger()
