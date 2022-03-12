from typing import Any, List

from psaw import PushshiftAPI

from .log import log_generator

logger = log_generator(__name__)


def fetch_submissions(sub, since, until):
    """
    Fetches a list of Submission objects from Pushshift.
    We use this to backfill data missing from Reddit's API where required.

    :param sub: Subreddit to search
    :param since: Date from which to pull data, in Unix epoch format
    :param until: Date until which to pull data, in unix epoch format
    :returns: List of submission objects
    """
    pushshift = PushshiftAPI()

    logger.info("Fetching historical submissions from Pushshift.")
    logger.debug(f"Since: {since}")
    logger.debug(f"Until: {until}")

    # submissions() has been removed from the Reddit API.
    submissions = pushshift.search_submissions(before=until, after=since, subreddit=sub)
    submissions: List[Any] = [x for x in submissions]
    logger.info(f"Fetched {len(submissions)} submissions from Pushshift.")

    return submissions
