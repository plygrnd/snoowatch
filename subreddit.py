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

        prawinit = json.loads(s3.get_object(Bucket='timewasterbot', Key='praw.json')
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
                'Time': datetime.utcfromtimestamp(int(action.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
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
            "author": post.author.name,
        }

        if self.is_banned:
            submission['author_banned'] = True

        return submission

    def is_banned(self, redditor):
        """
        PRAW returns 200 even if a redditor was banhammered by the admins, blergh.  https://redd.it/7hfolk
        Checks if a user was banned by the reddit admins.

        :param redditor: Reddit username
        :returns: Bool(is_banned)
        """
        logger.info('Checking if u/{} was banned by the admins.'.format(redditor))
        redditor = self.redditor(redditor)

        # MUH EASTER EGGZ
        if redditor == 'niezo':
            return 'https://i.imgur.com/hlg0Kti.jpg'
        if redditor == 'BMO':
            return 'http://www.artsillustrated.com/wp-content/uploads/2016/10/Justin-Johnson-.jpg'

        has_suspended_attr = hasattr(redditor, 'is_suspended')
        if has_suspended_attr:
            logger.debug('is_suspended available.')
            is_suspended = getattr(redditor, 'is_suspended')
            if is_suspended:
                logger.info('u/{} has gone to Valhalla. BYE FELICIA, BYEEE!"'.format(redditor))
            else:
                logger.info('u/{} is still with us. Odin be praised!'.format(redditor))
            return is_suspended
        else:
            logger.debug('is_suspended unavailable')
            logger.warn('No data available. u/{} is __probably__ active'.format(redditor))
            return False

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
            # We need to check if a post author deleted their account.
            try:
                author = self.redditor(post.author.name)
                redditor_since = datetime.utcfromtimestamp(int(post.author.created_utc)).strftime('%Y-%m-%d %H:%M:%S')
            except exceptions.NotFound as e:
                author = '[deleted]'
                redditor_since = '[deleted]'

            is_banned = self.is_banned(post.author.name)
            if is_banned is True:
                redditor_since = '[banned]'
                is_banned = True
            else:
                is_banned = False

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "author": {
                    "name": author,
                    "redditor_since": redditor_since,
                    "is_banned": is_banned
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
            trafficstats['Hour'][datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2]
            }

        for data in traffic['day']:
            trafficstats['Day'][datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2],
                'Subscriptions': data[3]
            }

        for data in traffic['month']:
            trafficstats['Month'][datetime.utcfromtimestamp(data[0]).strftime('%Y-%m-%d %H:%M:%S')] = {
                'Uniques': data[1],
                'Pageviews': data[2]
            }
