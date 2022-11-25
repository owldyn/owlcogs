from .base import AbstractProcessor
import re

class RedditProcessor(AbstractProcessor):
                             # https?://old/www?.reddit.com/r/sub /comments?/postid  /shortname/commentid
    link_regex = re.compile(r'(http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/)([^/]*)(/[^/]*/?)([^/]*)?.*')
    short_reddit_regex = re.compile(r'(http.?://(.?)\.?redd.it/)(.*)?')
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
            return self._process_short_link(url, audio, **kwargs)
        
        return self._process_long_link(url, audio, **kwargs)

    def _process_short_link(self, url, audio, **kwargs):
        """Processes a short reddit link"""
        