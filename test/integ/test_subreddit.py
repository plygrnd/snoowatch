#!/usr/bin/python

from tinkerbell import subreddit

s = subreddit.Stats(aws_profile='tinkerbell')


def test_fetch_reddit_account():
    u = s.fetch_reddit_account('beefythecat')
    assert u
