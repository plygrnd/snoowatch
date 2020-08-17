#!/usr/bin/python3

import argparse

from datetime import datetime
from sys import argv

from snoowatch.log import log_generator
from snoowatch.reddit import Subreddit
from snoowatch.search import ESClient

parser = argparse.ArgumentParser()

parser.add_argument("-k", "--reddit-api-secret", help="AWS Secrets Manager Secret")
parser.add_argument("-r", "--aws-region", help="AWS Region")
parser.add_argument("-s", "--subreddit", help="Subreddit to watch")
args = parser.parse_args()


class Watcher(object):
    def __init__(self, subreddit):
        subreddit = args.subreddit if args.subreddit else None
        self.reddit = Subreddit(args.reddit_api_secret, args.aws_region)
        """
        self.es = ESClient(
            aws_profile="snoowatch", sub="anxiety", cluster_url="172.18.0.1"
        )

        self.search = Search(using=self.es.cluster, index="anxiety")
        self.results = self.search.query("range", created={"lte": "now"}).execute()
        self.last_post = datetime.strftime(
            datetime.strptime(self.results[0]["created"], "%Y-%m-%d %H:%M:%S").date(),
            "%Y/%m/%d",
        )"""

        self.logger = log_generator(__name__)

        test_redditor = "beefythecat"
        r = self.reddit.get_redditor(test_redditor)

    """
    def watch_subreddit(self):

        self.logger.info("Time of last post in index: {}".format(self.last_post))

        new_posts = self.reddit.fetch_submissions(
            self.last_post, datetime.strftime(datetime.now().date(), "%Y/%m/%d")
        )

        parsed_new_posts = self.reddit.parse_submissions(new_posts)

        self.es.index_submissions(parsed_new_posts)

        self.logger.info("Index updated. Continuing to stream new submissions.")
        self.es.stream_submissions()
        """


if __name__ == "__main__":
    logger = log_generator(__name__)
    subreddit = args.subreddit if args.subreddit else None
    subreddit = Watcher(subreddit)
    """
    logger.info(f"Starting to monitor r/{subreddit}")
    subreddit.watch_subreddit()
    """
