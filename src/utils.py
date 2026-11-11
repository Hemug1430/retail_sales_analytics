
import logging
from pathlib import Path
from datetime import datetime
from config import LOG_FOLDER


def setup_logger():

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_file = LOG_FOLDER / "application.log"

    file_handler = logging.FileHandler(log_file)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()

logger.info("Logger setup completed successfully")



