import logging


def logger(name) -> logging.getLogger():
    """
    Emit logs to stdout
    :returns: logging.logger() object
    """
    log_client = logging.getLogger(__name__)
    log_client.setLevel(logging.DEBUG)

    # Create a console logger for when this runs as a streaming processor
    # TODO: implement streaming processing
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.DEBUG)

    # It has to be readable
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_logger.setFormatter(formatter)
    log_client.addHandler(console_logger)

    return log_client
