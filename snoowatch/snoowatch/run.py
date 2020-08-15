#!/usr/bin/python3

from datetime import datetime
from sys import argv
from time import sleep

from snoowatch.snoowatch import Watcher

if __name__ == "__main__":
    logger = logger(__name__)
    subreddit = Watcher(argv[1])
    logger.info(f"Starting to monitor r/{subreddit}")
    subreddit.watch_subreddit()

