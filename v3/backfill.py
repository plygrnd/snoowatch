# Disabled until we figure out how to do this quicker.
# https://github.com/plygrnd/tinkerbell/issues/3
if not post.author.name:
    data['author']['author_name'] = '[deleted]'
elif hasattr(author, 'is_suspended'):
    if getattr(author, 'is_suspended'):
        data['author']['account_name'] = author.name
        data['author']['is_banned'] = True
else:
    data['author']['author_name'] = post.author.name
    account_created = datetime.utcfromtimestamp(int(author.created_utc))
    data['author']['account_created'] = str(account_created)
    data['author']['account_age'] = abs((datetime.now() - account_created).days)
    data['author']['is_banned'] = False
