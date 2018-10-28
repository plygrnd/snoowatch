#!/usr/bin/python
# coding: utf-8

import json
from datetime import datetime

import fnmatch
import os
from praw import Reddit
from prawcore import exceptions
from psaw import PushshiftAPI

from snoowatch.log import log_generator

logger = log_generator(__name__)


def get_reddit_creds(path):
    for root, dirs, files in os.walk(path):
        for filename in fnmatch.filter(files, 'reddit_auth'):
            creds = os.path.join(root, filename)

            return creds


class RedditIndexer(Reddit):
    def __init__(self, requestor_kwargs=None, sub=None):

        self.requestor_kwargs = requestor_kwargs

        reddit_auth = get_reddit_creds('/run/secrets')
        if not reddit_auth:
            reddit_auth = get_reddit_creds('..')

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
        submissions = [x for x in self.pushshift.search_submissions(before=until, after=since, subreddit=self.sub)]
        logger.info('Fetched {} submissions from Pushshift.'.format(len(submissions)))

        return submissions

    def enrich_and_parse_submissions(self, submissions):
        """
        Parses out useful data from submissions.
        This has been trimmed like crazy from v1 because Reddit's new API is shit
        and doesn't return stuff like submission karma, at least not that I can see.
        TODO: Figure out how to get better metrics for submissions (views, karma etc)

        :param submissions: name of submissions variable to parse
        :returns: JSONified list of submissions
        """

        metrics = []

        for post in submissions:

            creation_time = datetime.utcfromtimestamp(
                int(post.created_utc)
            ).strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "id": post.id,
                "url": post.url,
                "created": creation_time,
                "title": post.title,
                "author": post.author
            }

            try:
                data['submission_text'] = {
                    "text": post.selftext,
                    "source": "pushshift"
                }
            except(AttributeError, KeyError):
                logger.debug(
                    "Could not fetch submission text from Pushshift. Calling Reddit for post {}".format(post.id))
                data['submission_text'] = {
                    "text": self.submission(post.id).selftext,
                    "source": "reddit"
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
