#!/usr/bin/python

import json
import sys

import puni

import subreddit

reddit = subreddit.Stats()
sub = reddit.subreddit(sys.argv[1])
notes = puni.UserNotes(reddit, sub)

with open(sys.argv[2]) as file:
    automod_banned_users = [str(acc)for acc in file.readlines()]

active_accounts = []
deleted_accounts = []

for banned_user in automod_banned_users:
    try:
        active_accounts.append(
            dict(
                username=reddit.redditor(banned_user).fullname,
                usernotes=[note.note for note in notes.get_notes(banned_user) if note]
            ))
    except:
        deleted_accounts.append(
            dict(
                username=banned_user,
                usernotes=[note.note for note in notes.get_notes(banned_user) if note]
            ))

summary = json.dumps([{"active": active_accounts, "deleted": deleted_accounts}], indent=4)

print(summary)
print("Active users: {}".format(len(summary['active'])))
print("Deleted users {}".format(len(summary['deleted'])))
