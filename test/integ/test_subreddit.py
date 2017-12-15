#!/usr/bin/python

import subreddit

s = subreddit.Stats(aws_profile='tinkerbell')


def test_is_banned():
    u = s.is_banned('beefythecat')
    assert u == False
