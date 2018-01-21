#!/usr/bin/python3

import logging

from datetime import datetime
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

        super().__init__()

    def initialise_es_index(self):
        # cyka blyat fucking fielddata bullshit
        # pizdec elasticsearch not knowing what i want /s
        subreddit_index_mapping = {
            "mappings": {
                "post": {
                    "properties": {
                        "created": {
                            "type": "date",
                            "format": "yyyy-MM-dd HH:mm:ss"
                        },
                        "author": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "keyword"},
                                "created": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss"},
                            }},
                        "flair": {
                            "type": "keyword"
                        },
                        "domain": {
                            "type": "keyword"
                        }
                    }
                }
            }
        }
        if not self.cluster.client.indices.exists(self.sub):
            index = self.cluster.client.indices.create(
                index=self.sub,
                body=subreddit_index_mapping
            )

            logger.info(index)
            return index
        else:
            logger.error('Index {} already exists.'.format(self.sub))

    def index_submissions(self, data):
        for post in data:
            put_index = self.cluster.index(
                index=self.sub,
                doc_type='post',
                id=post['id'],
                body=post
            )
            logger.debug(put_index)

        logger.debug('Indexed {} posts'.format(len(data)))

    def stream_submissions(self):
        """
        Fetches a stream of submissions from a subreddit,
        parses them and indexes the results into Elasticsearch.
        Intended to run in a loop, which probably isn't the best way to do this.
        TODO: Find a better way to do this.
        """

        logger.info('Starting submission stream')
        substream = self.reddit.subreddit(self.sub).stream.submissions()

        for post in substream:
            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(
                    int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "submission_text": post.selftext,
                "domain": post.domain,
                "author": {
                    "author_name": str(post.author),
                    "account_created": None,
                    "account_age": None,
                    "is_banned": None
                },
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs
            }

            indexed_data = self.cluster.client.index(
                doc_type='post',
                index=self.sub,
                id=data['id'],
                body=data
            )

            logger.debug(indexed_data)