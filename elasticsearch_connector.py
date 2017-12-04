#!/usr/bin/python3

import json
import logging

from elasticsearch import Elasticsearch

import subreddit

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


class ElasticsearchConnector(Elasticsearch):
    def __init__(self, aws_profile, sub_name, cluster_url):
        self.reddit = subreddit.Stats(aws_profile, sub=sub_name)
        self.sub_name = sub_name
        self.cluster = Elasticsearch(host=cluster_url)

    def initialise_es_index(self):
        with open('mappings.json', 'r') as mapping:
            if not self.cluster.indices.exists(self.sub_name):
                index = self.cluster.indices.create(
                    index=self.sub_name,
                    body=json.load(mapping)
                )

                logger.info(index)
            else:
                logger.error('Index {} already exists.'.format(self.sub_name))
                index = self.sub_name

        return index

    def fetch_subreddit_data(self, since, until):

        logger.info('Fetching post data for r/{} from {}'.format(
            self.sub_name,
            since
        ))

        data = [item for item in self.reddit.fetch_submissions(since, until)]

        for post in data:
            logger.debug(post)
            put_index = self.cluster.index(
                index=self.sub_name,
                doc_type='post',
                id=post['id'],
                body=post
            )
            logger.debug(put_index)

        logger.debug('Indexed {} posts'.format(len(data)))
