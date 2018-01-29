#!/usr/bin/python

import subreddit

s = subreddit.Stats(aws_profile='tinkerbell')


<<<<<<< HEAD
def test_fetch_reddit_account():
    u = s.fetch_reddit_account('beefythecat')
    assert u
=======
def test_is_banned():
    u = s.is_banned('beefythecat')
    assert u is False
>>>>>>> 7923c2d3ca38d1d6920d44c702d6e6e187d22a36
