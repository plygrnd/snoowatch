#!/usr/bin/python3

from datetime import datetime
from sys import argv

from reddit import Subreddit
from search import ESClient


class Watcher(object):
    def __init__(self, subreddit):
        self.reddit = Subreddit(reddit_api_secret_name, aws_region, subreddit=None)
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


if __name__ == "__main__":
    logger = log_generator()
    subreddit = Watcher(argv[1])
    logger.info(f"Starting to monitor r/{subreddit}")
    subreddit.watch_subreddit()
