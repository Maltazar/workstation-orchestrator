from models.config import Configuration
from logger.logger import logger


def prepare_handler(config: Configuration) -> Configuration:
    logger.info("Running prepare handler")
    config = config.prepare.run(config)
    logger.success("Prepare loaded")
    return config


def run_handler(config: Configuration) -> Configuration:
    """Run the handler for each OS"""
    logger.debug("Starting run_handler")
    for os_name in config.get_target_os():
        if os_name == "none":
            continue

        logger.info(f"Validating {os_name} configuration")
        if not hasattr(config, os_name):
            logger.warning(f"No configuration found for {os_name}")
            continue

        # Set the active OS being processed
        config.set_active_os(os_name)
        logger.log_active_config(os_name)

        logger.info(f"Running {os_name} module")
        os_config = getattr(config, os_name)
        if os_config:
            logger.info(f"Processing {os_name} configuration")
            # os_config.run()
            for field_name in os_config.model_fields.keys():
                if field_name not in ["prepare"]:
                    module = getattr(os_config, field_name)
                    if module:
                        logger.info(f"Running {field_name} module")
                        module.run()
                        logger.success(f"{field_name} module finished")

    return config
