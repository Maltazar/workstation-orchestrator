from models.base.prepare import PrepareModel
from models.config import Configuration
from helpers.helper import download_resource, merge_yaml
from logger.logger import logger
from models.base_model import ExecutionOrder


def _run_prepare_config(prepare: PrepareModel, config: Configuration) -> Configuration:
    logger.info("Running prepare")

    if prepare.download:
        for name, group in prepare.download.items():
            logger.info(f"Downloading items group - {name}")
            for resource in group.resources:
                logger.info(f"Downloading {name} from {resource.url}")
                download_resource(resource)

    if prepare.command:
        prepare.command.run(ExecutionOrder.TARGET)

    if prepare.merge_yamls:
        for name, group in prepare.merge_yamls.items():
            if group.enabled:
                logger.info(f"Merging {name}")
                for yaml in group.yamls:
                    logger.info(f"Merging {yaml} into config")
                    config = merge_yaml(yaml, config)
    return config


def run_prepare(prepare: PrepareModel, config: Configuration):
    config = _run_prepare_config(prepare, config)

    for os_name in config.get_target_os():
        if os_name != "none":
            logger.info(f"Running {os_name} module")
            os_config = getattr(config, os_name)
            if os_config and os_config.prepare:
                logger.info(f"Merging {os_name} specific config")
                config = _run_prepare_config(os_config.prepare, config)
    return config.merge_os_specific_configs(exclude=["prepare"])
