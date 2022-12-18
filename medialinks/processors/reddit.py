import re

import praw

from .base import AbstractProcessor, MessageBuilder


class RedditProcessor(AbstractProcessor):
    """processor for reddit"""
    # https?://old/www?.reddit.com/r/sub /comments?/postid  /shortname/commentid
    link_regex = re.compile(
        r'(http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/)([^/]*)(/[^/ ]*/?)([^/ ]*)?[^ ]*')
    short_reddit_regex = re.compile(r'(http.?://(.?)\.?redd.it/)([^ ]*)?')
    regex_checks = [short_reddit_regex, link_regex]

    def __init__(self) -> None:
        super().__init__()
        self.spoiler = None
        self.audio = None
        self.url = None
        self.reddit = praw.Reddit(
            "Hoobot", user_agent="discord:hoobot:2.0 (by u/owldyn)")
        self.footer = None

    class MessageBuilder(MessageBuilder):
        def prettify_embed(self, output):
            pass

    def verify_link(self, url, audio, spoiler=False, **kwargs):
        """Verifies the url is valid."""
        # Check both types of reddit urls.
        print(f'rspolier: {spoiler}!', flush=True)
        
        self.spoiler = spoiler
        self.url = url
        self.audio = audio
        short_link = False
        match = self.link_regex.match(url)
        if not match:
            match = self.short_reddit_regex.match(url)
            short_link = True

        if not match:
            raise self.InvalidURL(
                'URL did not match what I expect from Reddit!')

        if short_link:
            return self._process_short_link(match)

        reddit_post = self.reddit.submission(url=url)
        return self.process_post(reddit_post, match)

    def _process_short_link(self, match):
        """Processes a short reddit link"""
        if match.group(2):
            # Just get the first post, that's usually going to be the right one.
            # If it's not, well they shoulda linked the reddit page not the media for it.
            reddit_post = next(self.reddit.info(url=self.url))
            self.footer = 'This post may not be the one you expect... Send the reddit post url for more accuracy!'
        else:
            submission_id = match.group(3)
            if not submission_id:
                raise self.InvalidURL(
                    'Could not fetch reddit post for given url!')
            reddit_post = self.reddit.submission(id=submission_id)

        # Update the match to the full url.
        match = self.link_regex.match(self._reddit_link(reddit_post))
        return self.process_post(reddit_post, match)

    def process_post(self, reddit_post, match):
        """Processes and returns the info from a post"""
        if reddit_post.is_self:
            return self._process_self(reddit_post, match)

        imglink = reddit_post.url
        if "preview.redd.it" in imglink:
            imglink = imglink.replace("preview.redd", "i.redd")
        elif "/imgur.com" in imglink:
            imglink = imglink.replace("/imgur.com", "/i.imgur.com")
            if ".png" not in imglink and ".jpg" not in imglink and ".gif" not in imglink:
                imglink = imglink + ".png"

        check_videos = ['v.redd.it', 'gfycat', 'streamable']

        if (True in [check in imglink for check in check_videos] or
           ("imgur" in imglink and ".gifv" in imglink)):
            return self._process_video(reddit_post, match)
        if "reddit.com/gallery" in imglink:
            return self._process_gallery(reddit_post, match)

        # Image processing will always be a fallback. Worst case is the preview doesn't work.
        return self._process_image(reddit_post, match)

    @staticmethod
    def _reddit_link(reddit_post):
        return f'https://reddit.com{reddit_post.permalink}'

    def _process_comments(self, match):
        if match.group(4):
            comment_info = self.reddit.comment(match.group(4))
            title = f'Comment by {comment_info.author.name}'

            if (len(title + comment_info.body) < 4096) and (len(title) < 255):
                return self.MessageBuilder(title=title, description=comment_info.body, spoiler=self.spoiler)
            return self.MessageBuilder(title=title, description=f'Comment is too long to post in discord! [Read it here!](https://reddit.com{comment_info.permalink})')
        return None

    def _process_self(self, reddit_post, match):
        self_text = reddit_post.selftext
        title = reddit_post.title
        comments = self._process_comments(match)
        if len(self_text) < 4096:
            if len(title) > 255:
                return f"**{title}**\n\n{self_text}"
            if not self.spoiler:
                self_text = self_text.replace(">!", "||").replace("!<", "||")
            return {'post': self.MessageBuilder(title=title, url=self.url, description=self_text, footer=self.footer, spoiler=self.spoiler), 'comments': comments}
        raise self.InvalidURL('Self post is too long!')

    def _process_video(self, reddit_post, match):
        title = reddit_post.title
        comments = self._process_comments(match)
        if len(title) > 255:
            # Just trim it
            title = title[:254]
        video = self._generic_video_dl(
            url=self._reddit_link(reddit_post), audio=self.audio)
        return {'post': self.MessageBuilder(title=title, url=self.url, spoiler=self.spoiler, video=video, footer=self.footer), 'comments': comments}

    def _process_image(self, reddit_post, match):
        title = reddit_post.title
        comments = self._process_comments(match)
        return {'post': self.MessageBuilder(title=title, url=self.url, image_url=reddit_post.url, spoiler=self.spoiler, footer=self.footer), 'comments': comments}

    def _process_gallery_multiple_embeds(self, reddit_post, match):
        """posts a gallery in order, This uses multiple embeds which isn't supported in the current version of redbot (3.4)"""
        title = reddit_post.title
        comments = self._process_comments(match)
        gallery = []
        discord_max_preview = 5
        ids = [i['media_id'] for i in reddit_post.gallery_data['items']]
        for id in ids:
            url = reddit_post.media_metadata[id]['p'][0]['u']
            url = url.split("?")[0].replace("preview", "i")
            gallery.append(url)
        return {'post': self.MessageBuilder(title=title, url=self.url, spoiler=self.spoiler, image_url=gallery, footer=self.footer), 'comments': comments}

    def _process_gallery(self, reddit_post, match):
        """posts a gallery in order, only 5 per message or discord won't preview them all"""
        title = reddit_post.title
        comments = self._process_comments(match)
        gallery = []
        discord_max_preview = 5
        ids = [i['media_id'] for i in reddit_post.gallery_data['items']]
        for id in ids:
            url = reddit_post.media_metadata[id]['p'][0]['u']
            url = url.split("?")[0].replace("preview", "i")
            gallery.append(url)
        messages = []
        while len(gallery) > 0:
            message = ""
            i = 0
            while i < discord_max_preview:
                i += 1
                if len(gallery) > 0:
                    message += gallery.pop(0)
                    message += '\n'
            messages.append(self.MessageBuilder(
                spoiler=self.spoiler, content=message, footer=self.footer))
        messages.append(self.MessageBuilder(
            spoiler=self.spoiler, content=title, footer=self.footer))
        return {'post': messages, 'comments': comments}
