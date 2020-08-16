#!/usr/bin/python3
# coding: utf-8

from datetime import datetime

from log import log_generator
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch_dsl import Search

from .reddit import Subreddit

logger = log_generator(__name__)


class ESClient(Elasticsearch):
    def __init__(self, aws_profile, sub, cluster_url):
        self.reddit = Subreddit(aws_profile, sub=sub)
        self.sub = sub
        self.cluster = Elasticsearch(
            host=cluster_url, connection_class=RequestsHttpConnection
        )

        super(Elasticsearch).__init__()

    def initialize_index(self):
        """
        Initializes the Elasticsearch index with field data specific to a subreddit
        :return:
        """
        subreddit_index_mapping = {
            "mappings": {
                "post": {
                    "properties": {
                        "created": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss"},
                        "author": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "keyword"},
                                "created": {
                                    "type": "date",
                                    "format": "yyyy-MM-dd HH:mm:ss",
                                },
                            },
                        },
                        "flair": {"type": "keyword"},
                        "domain": {"type": "keyword"},
                    }
                }
            }
        }
        if not self.cluster.indices.exists(self.sub):
            index = self.cluster.indices.create(
                index=self.sub, body=subreddit_index_mapping
            )

            logger.info(index)
            return index
        else:
            logger.error("Index {} already exists.".format(self.sub))

    def index_submissions(self, data):
        for post in data:
            put_index = self.cluster.index(
                index=self.sub, doc_type="post", id=post["id"], body=post
            )
            logger.debug(put_index)

        logger.debug("Indexed {} posts".format(len(data)))

    def stream_submissions(self):
        """
        Fetches a stream of submissions from a subreddit,
        parses them and indexes the results into Elasticsearch.
        Intended to run in a loop, which probably isn't the best way to do this.
        TODO: Find a better way to do this.
        """

        logger.info("Starting submission stream")
        submission_stream = self.reddit.subreddit(self.sub).stream.submissions()

        for post in submission_stream:
            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
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
                    "is_banned": None,
                },
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs,
            }

            indexed_data = self.cluster.index(
                doc_type="post", index=self.sub, id=data["id"], body=data
            )

            logger.debug(indexed_data)

    def get_traffic_stats(self):

        traffic = self.sub.traffic()

        trafficstats = {"Hour": {}, "Day": {}, "Month": {}}

        for data in traffic["hour"]:
            trafficstats["Hour"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2]}

        for data in traffic["day"]:
            trafficstats["Day"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2], "Subscriptions": data[3]}

        for data in traffic["month"]:
            trafficstats["Month"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2]}


class Watcher(object):
    def __init__(self, subreddit):
        self.reddit = Subreddit(aws_profile="snoowatch", sub=subreddit)
        self.es = ESClient(
            aws_profile="snoowatch", sub="anxiety", cluster_url="172.18.0.1"
        )

        self.search = Search(using=self.es.cluster, index="anxiety")
        self.results = self.search.query("range", created={"lte": "now"}).execute()
        self.last_post = datetime.strftime(
            datetime.strptime(self.results[0]["created"], "%Y-%m-%d %H:%M:%S").date(),
            "%Y/%m/%d",
        )

        self.logger = logger(__name__)

    def watch_subreddit(self):

        self.logger.info("Time of last post in index: {}".format(self.last_post))

        new_posts = self.reddit.fetch_submissions(
            self.last_post, datetime.strftime(datetime.now().date(), "%Y/%m/%d")
        )

        parsed_new_posts = self.reddit.parse_submissions(new_posts)

        self.es.index_submissions(parsed_new_posts)

        self.logger.info("Index updated. Continuing to stream new submissions.")
        self.es.stream_submissions()
