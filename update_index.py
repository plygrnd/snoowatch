#!/usr/bin/python

from datetime import datetime

from elasticsearch_dsl import Search

from esclient import ESClient
from subreddit import Stats

reddit = Stats(aws_profile='tinkerbell', sub='anxiety')

es = ESClient(
    aws_profile='tinkerbell',
    sub='anxiety',
    cluster_url='http://172.18.0.1'
)

search = Search(using=es, index='anxiety')

results = search.query("range", created={'lte': 'now'}).execute()

last_post = datetime.strftime(
    datetime.strptime(results[0]['created'], '%Y-%m-%d %H:%M:%S').date(),
    '%Y/%m/%d'
)

print('Time of last post in index: {}'.format(last_post))

new_posts = reddit.fetch_submissions(
    last_post,
    datetime.strftime(datetime.now().date(), '%Y/%m/%d')
)

parsed_new_posts = reddit.parse_submissions(new_posts)

es.index_submissions(parsed_new_posts)

print('Index updated. Continuing to stream new submissions.')
es.stream_submissions()
