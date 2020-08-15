#!/usr/bin/python3
# coding: utf-8

import json
import os
import time

from datetime import datetime

import boto3
from .log import log_generator
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch_dsl import Search
from praw import Reddit
from prawcore import exceptions

logger = log_generator(__name__)


class ESClient(Elasticsearch):
    def __init__(self, aws_profile, sub, cluster_url):
        self.reddit = Subreddit(aws_profile, sub=sub)
        self.sub = sub
        self.cluster = Elasticsearch(
            host=cluster_url, connection_class=RequestsHttpConnection
        )

        super(Elasticsearch).__init__()

    def initialise_es_index(self):
        """
        Initializes the Elasticsearch index with field data specific to a subreddit
        :return:
        """
        subreddit_index_mapping = {
            "mappings": {
                "post": {
                    "properties": {
                        "created": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss"},
                        "author": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "keyword"},
                                "created": {
                                    "type": "date",
                                    "format": "yyyy-MM-dd HH:mm:ss",
                                },
                            },
                        },
                        "flair": {"type": "keyword"},
                        "domain": {"type": "keyword"},
                    }
                }
            }
        }
        if not self.cluster.indices.exists(self.sub):
            index = self.cluster.indices.create(
                index=self.sub, body=subreddit_index_mapping
            )

            logger.info(index)
            return index
        else:
            logger.error("Index {} already exists.".format(self.sub))

    def index_submissions(self, data):
        for post in data:
            put_index = self.cluster.index(
                index=self.sub, doc_type="post", id=post["id"], body=post
            )
            logger.debug(put_index)

        logger.debug("Indexed {} posts".format(len(data)))

    def stream_submissions(self):
        """
        Fetches a stream of submissions from a subreddit,
        parses them and indexes the results into Elasticsearch.
        Intended to run in a loop, which probably isn't the best way to do this.
        TODO: Find a better way to do this.
        """

        logger.info("Starting submission stream")
        submission_stream = self.reddit.subreddit(self.sub).stream.submissions()

        for post in submission_stream:
            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "title": post.title,
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "submission_text": post.selftext,
                "domain": post.domain,
                "author": {
                    "author_name": str(post.author),
                    "account_created": None,
                    "account_age": None,
                    "is_banned": None,
                },
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs,
            }

            indexed_data = self.cluster.index(
                doc_type="post", index=self.sub, id=data["id"], body=data
            )

            logger.debug(indexed_data)


class Subreddit(Reddit):
    def __init__(
        self,
        sub=None
    ):

        principal = os.getenv("AWS_ACCESS_KEY_ID")
        credential = os.getenv("AWS_SECRET_ACCESS_KEY")

        # TODO: implement Secrets Manager
        s3 = boto3.Session(
            aws_access_key_id=principal, aws_secret_access_key=credential
        ).client("s3")

        prawinit = json.loads(
            s3.get_object(Bucket="timewasterbot", Key="praw.json")["Body"]
            .read()
            .decode("utf-8")
        )

        super(Reddit).__init__(**prawinit)

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
            actions.append(
                {
                    "Name": action.mod.name,
                    "Action": action.action,
                    "Time": datetime.utcfromtimestamp(int(action.created_utc)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Details": action.details,
                    "Post": action.target_permalink,
                    "Post Title": action.target_title,
                    "Post Body": action.target_body,
                }
            )

        return actions

    def fetch_submission_by_id(self, post_id):
        """
        Fetch a single post by ID.
        :param post_id: Base-36 encoded post ID.
        :returns: Single submission
        """

        logger.info("Fetching post {}".format(post_id))

        post = self.submission(id=post_id)

        submission = {
            "title": post.title,
            "link": post.permalink,
            "url": post.url,
            "text": post.selftext,
            "author": self.fetch_reddit_account(post.author.name).name,
        }

        return submission

    def fetch_reddit_account(self, redditor):
        """
        Gets a reddit account or returns None if one is unavailable

        :param redditor: Reddit username
        :returns: self.redditor or None
        """
        logger.info("Getting account status for u/{} .".format(redditor))
        # We need to check if an account was deleted or shadowbanned
        # (both return prawcore.exceptions.NotFound)
        try:
            redditor = self.redditor(redditor)
            hasattr(redditor, "fullname")
            logger.info(f"u/{redditor.name} is a valid reddit account.")
        except exceptions.NotFound:
            logger.info(f"u/{redditor.name} either shadowbanned or deleted.")
            return

        # https://redd.it/3sbs31
        # Accounts created after 2015/11/10 will have the is_suspended attribute
        # All others will return nothing.
        has_suspended_attr = hasattr(redditor, "is_suspended")
        if has_suspended_attr:
            logger.debug("is_suspended available.")
            is_suspended = getattr(redditor, "is_suspended")
            if is_suspended:
                logger.info(f"u/{redditor} has been banned.")
                return
            else:
                logger.info(f"u/{redditor} has an active Reddit account")
            return redditor
        else:
            logger.debug("is_suspended unavailable")
            logger.warning(f"An account exists for u/{redditor}")
            return redditor

    def fetch_submissions(self, since, until):
        """
        Creates a list of submission objects.

        :param since: Date from which to pull data, in Unix epoch format
        :param until: Date until which to pull data, in unix epoch format
        :returns: List of submission objects
        """
        since = time.mktime(datetime.strptime(since, "%Y/%m/%d").timetuple())
        until = time.mktime(datetime.strptime(until, "%Y/%m/%d").timetuple())

        logger.info("Fetching submissions from Reddit.")
        submissions = [item for item in self.sub.submissions(since, until)]
        logger.info(f"Fetched {len(submissions)} submissions from Reddit.")

        return submissions

    @staticmethod
    def parse_submissions(submissions):
        """
        Parses out useful data from submissions

        :param submissions: name of submissions variable to parse
        :returns: JSON-formatted list of submissions
        """

        metrics = []

        for post in submissions:

            data = {
                "id": post.id,
                "url": post.url,
                "created": datetime.utcfromtimestamp(int(post.created_utc)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "title": post.title,
                "flair": post.link_flair_text,
                "views": post.view_count,
                "comment_count": post.num_comments,
                "submission_text": post.selftext,
                "domain": post.domain,
                "removed": post.removed,
                "author": {
                    "author_name": str(post.author),
                    "account_created": None,
                    "account_age": None,
                    "is_banned": None,
                },
                "karma": post.score,
                "upvotes": post.ups,
                "downvotes": post.downs,
            }

            # TODO: figure out how to do this quicker.
            # https://github.com/plygrnd/tinkerbell/issues/3
            if not post.author.name:
                data['author']['author_name'] = '[deleted]'
            elif hasattr(post.author, 'is_suspended'):
                if getattr(post.author, 'is_suspended'):
                    data['author']['account_name'] = post.author.name
                    data['author']['is_banned'] = True
            else:
                data['author']['author_name'] = post.author.name
                account_created = datetime.utcfromtimestamp(int(post.author.created_utc))
                data['author']['account_created'] = str(account_created)
                data['author']['account_age'] = abs((datetime.now() - account_created).days)
                data['author']['is_banned'] = False

            logger.debug(data)
            metrics.append(data)

        return metrics

    def get_traffic_stats(self):

        traffic = self.sub.traffic()

        trafficstats = {"Hour": {}, "Day": {}, "Month": {}}

        for data in traffic["hour"]:
            trafficstats["Hour"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2]}

        for data in traffic["day"]:
            trafficstats["Day"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2], "Subscriptions": data[3]}

        for data in traffic["month"]:
            trafficstats["Month"][
                datetime.utcfromtimestamp(data[0]).strftime("%Y-%m-%d %H:%M:%S")
            ] = {"Uniques": data[1], "Pageviews": data[2]}


class Watcher(object):
    def __init__(self, subreddit):
        self.reddit = Subreddit(aws_profile="snoowatch", sub=subreddit)
        self.es = ESClient(
            aws_profile="snoowatch", sub="anxiety", cluster_url="172.18.0.1"
        )

        self.search = Search(using=self.es.cluster, index="anxiety")
        self.results = self.search.query("range", created={"lte": "now"}).execute()
        self.last_post = datetime.strftime(
            datetime.strptime(self.results[0]["created"], "%Y-%m-%d %H:%M:%S").date(),
            "%Y/%m/%d",
        )

        self.logger = logger(__name__)

    def watch_subreddit(self):

        self.logger.info("Time of last post in index: {}".format(self.last_post))

        new_posts = self.reddit.fetch_submissions(
            self.last_post, datetime.strftime(datetime.now().date(), "%Y/%m/%d")
        )

        parsed_new_posts = self.reddit.parse_submissions(new_posts)

        self.es.index_submissions(parsed_new_posts)

        self.logger.info("Index updated. Continuing to stream new submissions.")
        self.es.stream_submissions()
