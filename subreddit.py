#!/usr/bin/python
# coding: utf-8

import logging
import json
import sys

from datetime import datetime
from multiprocessing import Pool

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

    def fetch_posts(self, since):
        """
        Grabs a bunch of data for posts to a subreddit.

        :param since: Date from which to pull data, in Unix epoch format
        :returns: List of posts
        """
        metrics = []

        logger.info('Fetching posts from Reddit API. This might take a while')
        posts = [item for item in self.sub.submissions(since)]
        logger.info('Fetched {} posts from Reddit.'.format(len(posts)))

        for post in posts:
            # We need to check if a post author deleted their account.
            try:
                author = post.author.name
                redditor_since = datetime.utcfromtimestamp(int(post.author.created_utc)).strftime('%Y-%m-%d %H:%M:%S')
            except exceptions.NotFound as e:
                author, redditor_since = '[deleted]'

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "author": {
                    "name": author,
                    "redditor_since": redditor_since
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
