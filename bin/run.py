#!/usr/bin/python3

from sys import argv

from snoowatch.log import log_generator
from snoowatch.snoowatch import Watcher


if __name__ == "__main__":
    logger = log_generator()
    subreddit = Watcher(argv[1])
    logger.info(f"Starting to monitor r/{subreddit}")
    subreddit.watch_subreddit()
