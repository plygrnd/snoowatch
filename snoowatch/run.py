#!/usr/bin/python3

from sys import argv

from snoowatch import Watcher

if __name__ == "__main__":
    logger = logger(__name__)
    subreddit = Watcher(argv[1])
    logger.info(f"Starting to monitor r/{subreddit}")
    subreddit.watch_subreddit()

