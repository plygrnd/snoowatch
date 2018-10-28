#!/usr/bin/python3

import secrets

import docker

from snoowatch.log import log_generator

logger = log_generator(__name__)


class Bootstrap(docker.Client):
    def __init__(self):
        self.docker_client = docker.Client(base_url='unix://var/run/docker.sock')

    def initialize_consul_acl(self):
        master_token: str = secrets.token_hex(32)
        acl_config = {
            "acl_datacenter": "tb1",
            "acl_master_token": master_token,
            "acl_default_policy": "deny",
            "acl_down_policy": "extend-cache"
        }
