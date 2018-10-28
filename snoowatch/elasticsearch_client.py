#!/usr/bin/python3

from datetime import datetime

from elasticsearch import Elasticsearch, RequestsHttpConnection

from snoowatch import log, reddit_helper

logger = log.log_generator(__name__)

class ESClient(Elasticsearch):
    def __init__(self, sub, cluster_url):
        self.reddit = reddit_helper.RedditIndexer(sub=sub)
        self.sub = sub
        self.cluster = Elasticsearch(
            host=cluster_url,
            connection_class=RequestsHttpConnection
        )

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
                        }
                    }
                }
            }
        }
        if not self.cluster.indices.exists(self.sub):
            index = self.cluster.indices.create(
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
            creation_time = datetime.utcfromtimestamp(
                int(post.created_utc)
            ).strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "id": post.id,
                "url": post.url,
                "created": creation_time,
                "title": post.title,
                "author": post.author.name,
                "submission_text": {
                    "text": post.selftext,
                    "source": "reddit"
                }
            }

            indexed_data = self.cluster.index(
                doc_type='post',
                index=self.sub,
                id=data['id'],
                body=data
            )

            logger.debug(indexed_data)
