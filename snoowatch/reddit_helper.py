#!/usr/bin/python
# coding: utf-8

import json
from datetime import datetime

import fnmatch
import os
from praw import Reddit
from prawcore import exceptions
from psaw import PushshiftAPI

from tinkerbell.log import log_generator

logger = log_generator(__name__)


def get_reddit_creds(path):
    for root, dirs, files in os.walk(path):
        for filename in fnmatch.filter(files, 'reddit_auth'):
            creds = os.path.join(root, filename)

            return creds

class Stats(Reddit):
    def __init__(self, requestor_kwargs=None, sub=None):

        self.requestor_kwargs = requestor_kwargs

        reddit_auth = get_reddit_creds('/run/secrets')

        with open(reddit_auth) as reddit_auth:
            reddit_auth = reddit_auth.read()
            prawinit = json.loads(reddit_auth)

        super().__init__(**prawinit)

        self.pushshift = PushshiftAPI()

        if sub:
            self.sub = self.subreddit(sub)

    def get_mod_log(self, since):
        """
        Gets mod actions

        :param since: Date from which to pull data, in Unix epoch format
        :returns: List of mod actions
        """

        actions = []

        for action in self.sub.mod.log(limit=since):
            actions.append({
                'Name': action.mod.name,
                'Action': action.action,
                'Time': datetime.utcfromtimestamp(
                    int(action.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                'Details': action.details,
                'Post': action.target_permalink,
                'Post Title': action.target_title,
                'Post Body': action.target_body
            })

        return actions

    def fetch_submission_by_id(self, post_id):
        """
        Fetch a single post by ID.
        :param post_id: Base-36 encoded post ID.
        :returns: Single submission
        """

        logger.info('Fetching post {}'.format(post_id))

        post = self.submission(id=post_id)

        submission = {
            "title": post.title,
            "link": post.permalink,
            "url": post.url,
            "text": post.selftext,
            "author": self.fetch_reddit_account(post.author.name).name
        }

        return submission

    def fetch_reddit_account(self, redditor):
        """
        Gets a reddit account or returns None if one is unavailable

        :param redditor: Reddit username
        :returns: self.redditor or None
        """
        logger.info('Getting account status for u/{} .'.format(redditor))
        # We need to check if an account was deleted or shadowbanned
        # (both return prawcore.exceptions.NotFound)
        try:
            redditor = self.redditor(redditor)
            hasattr(redditor, 'fullname')
            logger.info('u/{} is a valid reddit account.'.format(redditor.name))
        except exceptions.NotFound:
            logger.warning('u/{} either shadowbanned or deleted.'.format(redditor.name))
            return

        # https://redd.it/3sbs31
        # Accounts created after 2015/11/10 will have the is_suspended attribute
        # All others will return nothing.
        has_suspended_attr = hasattr(redditor, 'is_suspended')
        if has_suspended_attr:
            logger.debug('is_suspended available.')
            is_suspended = getattr(redditor, 'is_suspended')
            if is_suspended:
                logger.info('u/{} has been banned.'.format(redditor))
                return
            else:
                logger.info('u/{} has an active Reddit account'.format(redditor))
            return redditor
        else:
            logger.debug('is_suspended unavailable')
            logger.warning('An account exists for u/{}'.format(redditor))
            return redditor

    def fetch_submissions(self, since, until):
        """
        Creates a list of submission objects.

        :param since: Date from which to pull data, in Unix epoch format
        :param until: Date until which to pull data, in unix epoch format
        :returns: List of submission objects
        """

        logger.info('Fetching historical submissions from Pushshift.')
        logger.debug('Since: {}'.format(since))
        logger.debug('Until: {}'.format(until))

        # submissions() has been removed from PRAW because Reddit turned Cloudsearch off. 💩.
        # submissions = [item for item in self.sub.submissions(since, until)]
        submissions = self.pushshift.search_submissions(before=until, after=since, subreddit=self.sub)
        submissions = [x for x in submissions]
        logger.info('Fetched {} submissions from Pushshift.'.format(len(submissions)))

        return submissions

    @staticmethod
    def parse_submissions(submissions):
        """
        Parses out useful data from submissions

        :param submissions: name of submissions variable to parse
        :returns: JSONified list of submissions
        """

        metrics = []

        for post in submissions:
            # If something below is None, it's because Pushshift doesn't store that data.
            # We'll need to backfill it at a later stage by hitting the Reddit API.

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(
                    int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "flair": post.link_flair_richtext,
                "views": None,
                "comment_count": post.num_comments,
                "submission_text": post.selftext,
                "domain": post.domain,
                "removed": None,
                "author": {
                    "author_name": str(post.author),
                    "account_created": None,
                    "account_age": None,
                    "is_banned": None
                },
                "karma": None,
                "upvotes": None,
                "downvotes": None
            }

            """
            # Disabled until we figure out how to do this quicker.
            # https://github.com/plygrnd/tinkerbell/issues/3
            if not post.author.name:
                data['author']['author_name'] = '[deleted]'
            elif hasattr(author, 'is_suspended'):
                if getattr(author, 'is_suspended'):
                    data['author']['account_name'] = author.name
                    data['author']['is_banned'] = True
            else:
                data['author']['author_name'] = post.author.name
                account_created = datetime.utcfromtimestamp(int(author.created_utc))
                data['author']['account_created'] = str(account_created)
                data['author']['account_age'] = abs((datetime.now() - account_created).days)
                data['author']['is_banned'] = False
            """
            logger.debug(data)
            metrics.append(data)

        return metrics

    def get_traffic_stats(self):

        traffic = self.sub.traffic()

        trafficstats = {
            'Hour': {},
            'Day': {},
            'Month': {}
        }

        for data in traffic['hour']:
            trafficstats['Hour'][
                datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2]
            }

        for data in traffic['day']:
            trafficstats['Day'][
                datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2],
                'Subscriptions': data[3]
            }

        for data in traffic['month']:
            trafficstats['Month'][
                datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2]
            }
