#!/usr/bin/python3

import logging

import hvac

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


class VaultClient(hvac.Client):
    def __init__(self, shares, threshold, url):
        self.shares = shares
        self.threshold = threshold
        self.url = url

        self.client = hvac.Client(url=self.url)

    def bootstrap_vault(self):
        if self.client.is_initialized():
            logger.fatal('Vault is already initialised! Dying gracefully.')
        else:
            logger.info('Bootstrapping Vault!')

            init = self.client.initialize(self.shares, self.threshold)

            root_token = init['root_token']
            keys = init['keys']

            seed = {
                "root_token": root_token,
                "keys": keys
            }

            logger.info('Vault has been bootstrapped. Keys and root token follow.\n'
                        'Keep these safe and DO NOT SHARE THEM with unauthorised parties.\n'
                        'If you do, you risk compromising your credentials.')

            return seed
