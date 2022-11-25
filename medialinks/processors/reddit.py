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
            raise self.InvalidURL('URL did not match what I expect from Reddit!')

        if short_link:
            return self._process_short_link(match, url, audio)

        reddit_post = self.reddit.info()
        return self.process_post(reddit_post, match, audio)

    def _process_short_link(self, match, url, audio):
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
        match = self.link_regex.match(f'https://reddit.com{reddit_post.permalink}')
        return self.process_post(reddit_post, match, audio)

    def process_post(self, reddit_post, match, audio):
        if reddit_post.is_self:
            return self._process_self(reddit_post, match)

        imglink = reddit_post.url
        if "preview.redd.it" in imglink:
            imglink = imglink.replace("preview.redd", "i.redd")
        elif "/imgur.com" in imglink:
            imglink = imglink.replace("/imgur.com", "/i.imgur.com")
            if ".png" not in imglink and ".jpg" not in imglink and ".gif" not in imglink:
                imglink = imglink + ".png"


        if ("v.redd.it" in imglink or
           "gyfcat" in imglink or 
           ("imgur" in imglink and ".gifv" in imglink)):
            return self._process_video(reddit_post, match, audio)
        if "reddit.com/gallery" in imglink:
            return self._process_gallery(reddit_post, match)

        # Image processing will always be a fallback. Worst case is the preview doesn't work.
        return self._process_image(reddit_post, match)

    def _process_self(self, reddit_post, match):
        if len(selftext) < 1750:
            if len(title) > 255:
                return  # TODO make it actually post, but cleanly
            else:
                e = discord.Embed(title=title, description=selftext.replace(
                    ">!", "||").replace("!<", "||"))
                try:
                    await ctx.send(embed=e)
                    await ctx.message.edit(suppress=True)
                    if comment_info:
                        await self.post_comment(ctx, comment_info)
                    return
                except:
                    return
        else:
            raise self.InvalidURL('Self post is too long!')

    def _process_video(self, reddit_post, match, audio):
        pass

    def _process_image(self, reddit_post, match):
        pass

    def _process_gallery(self, reddit_post, match):
        pass
