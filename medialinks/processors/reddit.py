import re

import asyncpraw as praw

from .base import AbstractProcessor


class RedditProcessor(AbstractProcessor):
                             # https?://old/www?.reddit.com/r/sub /comments?/postid  /shortname/commentid
    link_regex = re.compile(r'(http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/)([^/]*)(/[^/]*/?)([^/]*)?.*')
    short_reddit_regex = re.compile(r'(http.?://(.?)\.?redd.it/)(.*)?')
    def __init__(self) -> None:
        super().__init__()
        self.reddit = praw.Reddit(
            "Hoobot", user_agent="discord:hoobot:2.0 (by u/owldyn)")
    def verify_link(self, url, audio, **kwargs):
        """Verifies the url is valid."""
        # Check both types of reddit urls.
        short_link = False
        match = self.link_regex.match(url)
        if not match:
            match = self.short_reddit_regex.match(url)
            short_link = True

        if not match:
            raise ValueError('URL did not match what I expect from Reddit!')

        if short_link:
            return self._process_short_link(match, url, audio, **kwargs)

        reddit_post = self.reddit.info()
        return self.process_post(reddit_post, match, audio, **kwargs)

    def _process_short_link(self, match, url, audio, **kwargs):
        """Processes a short reddit link"""
        if match.group(2):
            # Just get the first post, that's usually going to be the right one.
            # If it's not, well they shoulda linked the reddit page not the media for it.
            reddit_post = next(self.reddit.info(url=url))
        else:
            submission_id = match.group(3)
            if not submission_id:
                raise self.InvalidURL('Could not fetch reddit post for given url!')
            reddit_post = self.reddit.submission(id=submission_id)
        
        # Update the match to the full url.
        match = self.link_regex.match(reddit_post.url)
        return self.process_post(reddit_post, match, audio, **kwargs)

    def process_post(self, reddit_post, match, audio, **kwargs):
        pass
