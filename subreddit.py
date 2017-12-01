#!/usr/bin/python
# coding: utf-8

import json
from datetime import datetime

import boto3
from praw import Reddit


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
            data = ({
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": post.title,
                "author": post.author.name,
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comments": post.num_comments,
                "karma": post.score
            })
            metrics.append(data)
            print(data)

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
