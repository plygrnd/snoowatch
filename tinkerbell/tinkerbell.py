#!/usr/bin/python

from datetime import datetime

from elasticsearch_dsl import Search

from esclient import ESClient
from subreddit import Stats


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
        print(self.results)
        self.last_post = datetime.strftime(
            datetime.strptime(
                self.results[0]['created'], '%Y-%m-%d %H:%M:%S'
            ).date(),
            '%Y/%m/%d'
        )

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
    t = Tinkerbell()
    t.tinkerbell()
