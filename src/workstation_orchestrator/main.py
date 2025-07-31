import argparse
from pathlib import Path
from models.config import Configuration
from modules.processor import prepare_handler, run_handler
from logger.logger import logger
from helpers.helper import download_config


def parse_arguments():
    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument(
        "--os", type=str, required=False, help="Specify the operating system"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        required=False,
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    logger.info("Starting the application")
    config_path = args.config
    if args.config:
        if (
            args.config.startswith("http")
            or args.config.startswith("git")
            or args.config.startswith("ssh")
        ):
            config_path = download_config(args.config, verify_ssl=not args.insecure)
    if Path(config_path).exists():
        with open(config_path) as f:
            config_data = f.read()
        config = Configuration.from_yaml(config_data)
        if args.insecure:
            config.set_global_output("insecure", True)
    else:
        logger.error("Config file not found")
        return
    if args.os:
        config.set_target_os(args.os)
    logger.info("Config: loaded")
    config = prepare_handler(config)
    logger.info("Config: prepared")

    if logger.is_debug():
        Path("downloads").mkdir(parents=True, exist_ok=True)
        config.dump_yaml(Path("downloads/merged_config.yaml"))
        config.dump_json(Path("downloads/merged_config.json"))

    logger.info("Running the application")
    config = run_handler(config)
    logger.info("Application finished")


if __name__ == "__main__":
    main()
