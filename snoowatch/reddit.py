import time
import json

from datetime import datetime

from boto3.session import Session
from botocore.exceptions import ClientError
from praw import Reddit
from prawcore import exceptions

from .log import log_generator

logger = log_generator(__name__)


def get_reddit_api_creds(reddit_api_secret_name, aws_region):
    """
    This was mostly copied from the Secrets Manager-generated sample in the console.
    Variable names have been adjusted to suit this use case.

    This is a `script` application (more information in PRAW's documentation [here](https://praw.readthedocs.io/en/latest/getting_started/authentication.html#application-only-client-credentials).)
    As such, you do _not_ need to pass your Reddit username/password to the API; it requires your `user_agent`, `client_id` and `client_secret`.

    :param reddit_api_secret_name: The name of your Secrets Manager secret.
    :param aws_region: The AWS region within which your secret is stored
    :returns: JSON-formatted string containing required credentials.
    """

    # Create a Secrets Manager client
    session = Session()
    client = session.client(service_name="secretsmanager", region_name=aws_region)

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=reddit_api_secret_name
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        secret = get_secret_value_response["SecretString"]

        return secret


class Subreddit(Reddit):
    def __init__(self, reddit_api_secret_name, aws_region, subreddit=None):
        """
        Initializes a PRAW.Reddit instance.
        :param subreddit: OPTIONAL. Supply a subreddit name if you're working with subreddits.
        :returns: praw.Reddit
        """

        # Required: user_agent, client_id, client_secret
        reddit_creds = get_reddit_api_creds(reddit_api_secret_name, aws_region)

        prawinit = json.loads(reddit_creds)

        super().__init__(**prawinit)

        if subreddit:
            self.sub = self.subreddit(subreddit)

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

    def get_single_submission_by_id(self, post_id):
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
            "author": self.get_redditor(post.author.name).name,
        }

        return submission

    def get_redditor(self, redditor):
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
            logger.info(f"An account exists for u/{redditor}")
            return redditor

    def get_submissions(self, since, until):
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
                data["author"]["author_name"] = "[deleted]"
            elif hasattr(post.author, "is_suspended"):
                if getattr(post.author, "is_suspended"):
                    data["author"]["account_name"] = post.author.name
                    data["author"]["is_banned"] = True
            else:
                data["author"]["author_name"] = post.author.name
                account_created = datetime.utcfromtimestamp(
                    int(post.author.created_utc)
                )
                data["author"]["account_created"] = str(account_created)
                data["author"]["account_age"] = abs(
                    (datetime.now() - account_created).days
                )
                data["author"]["is_banned"] = False

            logger.debug(data)
            metrics.append(data)

        return metrics
