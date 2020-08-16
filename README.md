# SnooWatch

The friendly open-source Elasticsearch-based Subreddit analyzer

**NOTE** SnooWatch is currently being rewritten. DO NOT RELY ON THIS CODE AT PRESENT. It is not ready
for public consumption.

## Background

Snoowatch is a suite of tools to analyze submissions, users and comments on Reddit. It was initially created
to monitor a single subreddit, and ran within a homelab. It has since been refactored to run wholly
within the cloud, as an AWS Fargate/Elasticsearch application.

## Capabilities

* Index every post and comment within the subreddits of your choice
* Use Elasticsearch to monitor post/comment trends and create alerts as required

## Project status

Snoowatch is currently being developed. Current milestones:

* [x] Reddit API authentication via AWS Secrets Manager
* [x] Basic subreddit post/comment search and Reddit user introspection
* [ ] Elasticsearch integration
* [ ] Dockerized Elasticsearch ingestion mechanism
* [ ] Automated tool deployment via AWS CloudFormation
* [ ] Elasticsearch authentication mechanism

## How To Use SnooWatch

SnooWatch is designed to be deployed on [AWS](https://aws.amazon.com), since it makes use of Elastic Container Service/CloudFormation/Amazon Elasticsearch Service. You are welcome to modify the package as required to suit your deployment needs, or open an issue in this repo if you'd like SnooWatch to support other platforms.

## Reddit module

1. Get an AWS account, if you don't already have one.
1. [Create a Reddit API app](https://www.reddit.com/wiki/api). Give it a sensible User Agent. Note your `client_id`, `client_secret` and `user_agent`.
1. Once you've set your AWS account up, [create a secret](https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_create-basic-secret.html) in Secret Manager. Note the secret's name and AWS Region. The secret must be a JSON dictionary - its structure is below the line.
1. Get a set of AWS credentials via your preferred method (IAM credential pair, temporary session credentials, EC2 instance role credentials, etc). This author does **NOT** recommend using permanent credentials, and SnooWatch does not use them in production; it uses an IAM role attached to a Fargate task definition to authenticate to AWS services.In [2]: r = reddit.Subreddit("prod/reddit/API", "us-east-2", subreddit="funny")
`export`ing them in your terminal, by adding them to your `.aws/credentials` file, or by launching a resource with the appropriate permissions to obtain temporary credentials.
1. Instantiate a Reddit object as follows:

```bash
In [1]: import reddit
In [2]: r = reddit.Subreddit("prod/reddit/API", "us-east-2", subreddit="funny")
```

1. Have fun!

---

**Secrets Manager secret structure

```json
{
    "client_id": "foo",
    "client_secret": "bar",
    "user_agent": "script:MyAwesomeRedditScript:0.1 (by /u/you)"
}
```
