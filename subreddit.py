#!/usr/bin/python
# coding: utf-8

import logging
import json

from datetime import datetime

import boto3
from praw import Reddit

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger = logging.getLogger('prawcore')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

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

    def get_post_data(self, since):
        """
        Grabs a bunch of data for posts to a subreddit.

        :param since: Date from which to pull data, in Unix epoch format
        :returns: List of posts
        """

        posts = [post for post in self.sub.submissions(since, None)]
        metrics = []

        for post in posts:
            hot = [post for post in post.author.submissions.hot()]
            new = [post for post in post.author.submissions.new()]
            top = [post for post in post.author.submissions.top()]
            cont = [post for post in post.author.submissions.controversial()]

            hot_data = []
            new_data = []
            top_data = []
            cont_data = []

            for hot_post in hot:
                hot_data.append({
                    "subreddit": hot_post.subreddit.display_name,
                    "karma": hot_post.score,
                    "upvotes": hot_post.ups,
                    "downvotes": hot_post.downs,
                    "link": hot_post.shortlink,
                    "title": hot_post.title,
                    "created": hot_post.created_utc
                })

            for new_post in new:
                new_data.append({
                    "subreddit": new_post.subreddit.display_name,
                    "karma": new_post.score,
                    "upvotes": new_post.ups,
                    "downvotes": new_post.downs,
                    "link": new_post.shortlink,
                    "title": new_post.title,
                    "created": new_post.created_utc
                })

            for top_post in top:
                top_data.append({
                    "subreddit": top_post.subreddit.display_name,
                    "karma": top_post.score,
                    "upvotes": top_post.ups,
                    "downvotes": top_post.downs,
                    "link": top_post.shortlink,
                    "title": top_post.title,
                    "created": top_post.created_utc
                })

            for cont_post in cont:
                cont_data.append({
                    "subreddit": cont_post.subreddit.display_name,
                    "karma": cont_post.score,
                    "upvotes": cont_post.ups,
                    "downvotes": cont_post.downs,
                    "link": cont_post.shortlink,
                    "title": cont_post.title,
                    "created": cont_post.created_utc
                })

            previous_posts = {
                "hot": hot_data,
                "top": top_data,
                "new": new_data,
                "controversial": cont_data
            }

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "author": {
                    "name": post.author.name,
                    "redditor_since": datetime.utcfromtimestamp(int(post.author.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                    "previous_posts": previous_posts
                },
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs
            }

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

        return trafficstats
