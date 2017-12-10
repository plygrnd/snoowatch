#!/usr/bin/python
# coding: utf-8

import logging
import json
import time

from collections import defaultdict
from datetime import datetime

import boto3
from praw import Reddit
from prawcore import exceptions

# We want the logger to reflect the name of the module it's logging.

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console logger for when this runs as a streaming processor
# TODO: implement streaming processing
console_logger = logging.StreamHandler()
console_logger.setLevel(logging.DEBUG)

# It has to be readable

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_logger.setFormatter(formatter)
logger.addHandler(console_logger)


class Stats(Reddit):
    def __init__(self, aws_profile, site_name=None, requestor_class=None,
                 requestor_kwargs=None, sub=None, **config_settings):

        # TODO: implement instance role fetching
        s3 = boto3.Session(profile_name=aws_profile).client('s3')

        prawinit = json.loads(s3.get_object(
            Bucket='timewasterbot', Key='praw.json')
            ['Body'].read().decode('utf-8'))

        super().__init__(**prawinit)

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

        since = time.mktime(datetime.strptime(since, '%Y/%m/%d').timetuple())
        until = time.mktime(datetime.strptime(until, '%Y/%m/%d').timetuple())

        logger.info('Fetching posts from Reddit API. This might take a while')
        submissions = [item for item in self.sub.submissions(since, until)]
        logger.info('Fetched {} submissions from Reddit.'.format(len(submissions)))

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

            # Disabled until we figure out how to do this fast.
            # https://github.com/plygrnd/tinkerbell/issues/3
            # author = self.fetch_reddit_account(post.author.name)

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(
                    int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "submission_text": post.selftext,
                "domain": post.domain,
                "removed": post.removed,
                "num_reports": post.user_reports,
                "author": {
                    "author_name": str(post.author),
                    "account_created": None,
                    "account_age": None,
                    "is_banned": None
                },
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs
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
