#!/usr/bin/python

from datetime import datetime
from time import sleep

from elasticsearch_dsl import Search

from tinkerbell.esclient import ESClient
from tinkerbell.subreddit import Stats


class Tinkerbell(object):
    def __init__(self):
        self.reddit = Stats(aws_profile='tinkerbell', sub='anxiety')
        self.es = ESClient(
            aws_profile='tinkerbell',
            sub='anxiety',
            cluster_url='172.18.0.1'
        )

        self.search = Search(using=self.es.cluster, index='anxiety')
        self.results = self.search.query(
            "range", created={'lte': 'now'}
            ).execute()
        self.last_post_timestamp = datetime.strptime(self.results[0]['created'], '%Y-%m-%d %H:%M:%S').date()
        self.last_post = datetime.strftime(self.last_post_timestamp, '%Y/%m/%d')

    def tinkerbell(self):

        print('Time of last post in index: {}'.format(self.last_post))

        new_posts = self.reddit.fetch_submissions(
            self.last_post,
            datetime.strftime(datetime.now().date(), '%Y/%m/%d')
        )

        parsed_new_posts = self.reddit.parse_submissions(new_posts)

        self.es.index_submissions(parsed_new_posts)

        print('Index updated. Continuing to stream new submissions.')
        self.es.stream_submissions()


if __name__ == "__main__":
    print("Sleeping 75 seconds to let ES start up")
    sleep(75)
    print("OK I'm awake, doing the thing with the stuff")
    t = Tinkerbell()
    t.tinkerbell()
