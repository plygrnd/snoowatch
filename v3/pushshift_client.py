from typing import Any, List

from psaw import PushshiftAPI

from snoowatch.log import log_generator

logger = log_generator(__name__)


def fetch_submissions(sub, since, until):
    """
    Creates a list of submission objects.

    :param sub: Subreddit to search
    :param since: Date from which to pull data, in Unix epoch format
    :param until: Date until which to pull data, in unix epoch format
    :returns: List of submission objects
    """
    pushshift = PushshiftAPI()

    logger.info('Fetching historical submissions from Pushshift.')
    logger.debug('Since: {}'.format(since))
    logger.debug('Until: {}'.format(until))

    # submissions() has been removed from PRAW because Reddit turned Cloudsearch off. 💩.
    # submissions = [item for item in self.sub.submissions(since, until)]
    submissions = pushshift.search_submissions(before=until, after=since, subreddit=sub)
    submissions: List[Any] = [x for x in submissions]
    logger.info('Fetched {} submissions from Pushshift.'.format(len(submissions)))

    return submissions
