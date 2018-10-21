#!/usr/bin/python3

import docker
import hvac

from tinkerbell.log import log_generator

logger = log_generator(__name__)


class VaultClient(hvac.Client):
    def __init__(self, shares, threshold):
        self.shares = shares
        self.threshold = threshold

        self.docker_client = docker.Client(base_url='unix://var/run/docker.sock')
        # Right now, we expect a docker_gwbridge network to exist.
        # This will break for most people, so we need to make this more generic.
        # TODO: Make this more generic. #ihalp
        self.docker_gateway = self.docker_client.inspect_network('docker_gwbridge')['IPAM']['Config'][0]['Gateway']

        self.client = hvac.Client(url='http://{}:8200'.format(self.docker_gateway))

        super().__init__()

    def bootstrap_vault(self):
        if self.client.is_initialized():
            logger.fatal('Vault is already initialised! If you already provisioned your secrets and lost '
                         'the bootstrap creds, all is lost.')
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

