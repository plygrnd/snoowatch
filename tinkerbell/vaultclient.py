#!/usr/bin/python3

import hvac

from tinkerbell.log import log_generator

logger = log_generator(__name__)


class VaultClient(hvac.Client):
    def __init__(self, shares, threshold):
        self.shares = shares
        self.threshold = threshold

        self.client = hvac.Client()

        super().__init__()

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

            logger.info('Vault has been bootstrapped.')

            return seed
