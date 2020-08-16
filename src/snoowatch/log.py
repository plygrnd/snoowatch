import logging


def log_generator(__name__):
    # We want the logger to reflect the name of the module it's logging.

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a console logger for when this runs as a streaming processor
    # TODO: implement streaming processing
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.DEBUG)

    # It has to be readable

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_logger.setFormatter(formatter)
    logger.addHandler(console_logger)

    return logger
