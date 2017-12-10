#!/usr/bin/python3

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


class ESClient(Elasticsearch):
    def __init__(self, aws_profile, sub, cluster_url):
        self.reddit = subreddit.Stats(aws_profile, sub=sub)
        self.sub = sub
        self.cluster = Elasticsearch(host=cluster_url)

    def initialise_es_index(self):
        datetime_mapping = {
            "mappings": {
                "post": {
                    "properties": {
                        "created":  {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss"
                        }
                    }
                }
            }
        }
        if not self.cluster.indices.exists(self.sub):
            index = self.cluster.indices.create(
                index=self.sub,
                body=datetime_mapping
            )

            logger.info(index)
            return index
        else:
            logger.error('Index {} already exists.'.format(self.sub))

    def index_submissions(self, data):
        for post in data:
            logger.debug(post)
            put_index = self.cluster.index(
                index=self.sub,
                doc_type='post',
                id=post['id'],
                body=post
            )
            logger.debug(put_index)

        logger.debug('Indexed {} posts'.format(len(data)))
