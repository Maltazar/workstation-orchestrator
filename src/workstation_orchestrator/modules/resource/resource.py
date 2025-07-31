from models.base.resources import GroupedResources
from logger.logger import logger


def run_resource(resource: GroupedResources):
    logger.info(f"Running resource: {resource}")
