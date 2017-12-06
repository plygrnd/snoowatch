#!/usr/bin/python
# coding: utf-8

import logging
import json
import time

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

        # MUH EASTER EGGZ
        import random
        hedgies = [
            'https://i.imgur.com/vfhwwbb.jpg',
            'https://imgur.com/r/Hedgehog/KuAXs4T',
            'https://i.imgur.com/X5mEUMI.jpg',
            'https://i.imgur.com/SMoG8Cm.jpg',
            'https://i.imgur.com/Yw0K791.jpg',
            'https://i.imgur.com/Yll5vbG.jpg',
            'https://i.imgur.com/NrMKa8Y.jpg',
            'https://i.imgur.com/qVjFVb8.jpg',
            'https://i.imgur.com/2IM92GD.jpg',
            'https://i.imgur.com/Aa6hFDo.jpg'
            'https://imgur.com/r/Hedgehog/W8skE',
            'https://imgur.com/r/Hedgehog/UyXhP6u',
            'https://imgur.com/r/Hedgehog/FLDAdNZ',
            'https://i.imgur.com/9qqd2EVb.jpg'
        ]
        mods = ['niezo', 'muffinmedic', 'zelis42', 'bloo', 'remyschnitzel', 'ari', 'bmo', 'snitch', 'spaceblues',
                'vodkalimes', 'kimininegaiwo', 'alpha176', '10thtardis']

        if redditor in mods:
            return random.choice(hedgies)

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
            logger.warn('An account exists for u/{}'.format(redditor))
            return redditor

    def fetch_submissions(self, since, until):
        """
        Grabs a bunch of data for posts to a subreddit.

        :param since: Date from which to pull data, in Unix epoch format
        :param until: Date until which to pull data, in unix epoch format
        :returns: List of posts
        """

        """
        We need to convert input to a tuple,
        so we can convert it to a UNIX timestamp.
        """
        since = time.mktime(datetime.strptime(since, '%Y/%m/%d').timetuple())
        until = time.mktime(datetime.strptime(until, '%Y/%m/%d').timetuple())

        metrics = []

        logger.info('Fetching posts from Reddit API. This might take a while')
        posts = [item for item in self.sub.submissions(since, until)]
        logger.info('Fetched {} posts from Reddit.'.format(len(posts)))

        for post in posts:
            author = self.fetch_reddit_account(post.author.name)
            author_name = author.name
            account_created = datetime.utcfromtimestamp(int(author.created_utc))
            account_age = abs((datetime.now() - account_created).days)

            if not author:
                author_name = '[deleted]'
                account_created, account_age = None

            if hasattr(author, 'is_suspended'):
                if getattr(author, 'is_suspended'):
                    account_created = None
                    account_age = '[banned]'

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(
                    int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "author": {
                    "name": author_name,
                    "account_created": str(account_created),
                    "account_age": account_age,
                    "account_age": str(account_age)
                },
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs
            }

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
