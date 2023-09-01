import abc
import logging
from enum import Enum, auto
from io import BytesIO
from typing import Dict

import discord

from .libraries.ffmpeg import Ffmpeg
from .libraries.ydl import TemporaryYoutubeDL


class MessageBuilder(abc.ABC):
    """Builder for the message kwargs"""

    class MessageTypes(Enum):
        MULTI_EMBED = auto()
        PLAIN_MESSAGE = auto()
        TEXT_EMBED = auto()
        IMAGE_EMBED = auto()
        VIDEO = auto()

    def __init__(
        self,
        title=None,
        url=None,
        description=None,
        image_url=None,
        video=None,
        spoiler=False,
        content=None,
        footer=None,
        image=None,
    ) -> None:
        self.title = title[:255] if title else title # Cut the title off if it's too big.
        self.description = description
        self.image_url = image_url
        self.image = image
        self.video = video
        self.spoiler = spoiler
        self.url = url
        self.content = content
        self.footer = footer
        if title and len(title) > 255:
            self.footer += "\nTitle may be cut off."
        self._type = None
        self._send_kwargs = None

    @abc.abstractmethod
    def prettify_embed(self, output):
        """Prettify the embed (if it exists)"""

    @property
    def type(self):
        """Message type, will be from MessageTypes enum"""
        if not self._type:
            # Generate the kwargs, which will set the type.
            self.send_kwargs  # pylint: disable=pointless-statement
        return self._type

    @property
    def send_kwargs(self):
        """Generates the kwargs to send to ctx.send"""
        if not self._send_kwargs:
            output = {}
            if isinstance(self.image_url, list):
                self._multi_embed(output)
                self._type = self.MessageTypes.MULTI_EMBED
            elif self.image is not None:
                self._upload_image_embed(output)
                self._type = self.MessageTypes.IMAGE_EMBED
            elif self.content is not None:
                self._plain_message(output)
                self._type = self.MessageTypes.PLAIN_MESSAGE
            elif not self.video:
                self._general_embed(output)
                # Type is handled in the func here
            else:  # Should only be videos left at this point.
                self._video_embed(output)
                self._type = self.MessageTypes.VIDEO
            self.prettify_embed(output)
            self._set_url(output)
            self._add_footer(output)
            self._send_kwargs = output
        return self._send_kwargs

    def _set_url(self, output):
        if output.get("embed") and self.url:
            output.get("embed").url = self.url

    def _add_footer(self, output):
        if output.get("embed") and self.footer:
            output["embed"].set_footer(text=self.footer)

    def _plain_message(self, output):
        if self.spoiler:
            content = self._make_spoiler_text(self.content)
            output["content"] = content
        else:
            output["content"] = self.content

    def _multi_embed(self, output):
        embeds = []
        for image in self.image_url:
            embed = discord.Embed(title=self.title, url=self.url)
            embed.set_image(url=image)
            embeds.append(embed)
        output["embeds"] = embeds

    def _video_embed(self, output):
        embed = discord.Embed(title=self.title)
        output["embed"] = embed
        filename = f"SPOILER_{self.title}.mp4" if self.spoiler else f"{self.title}.mp4"
        output["file"] = discord.File(self.video, filename=filename)

    def _general_embed(self, output):
        embed_args = {"title": self.title}
        if self.description:
            if self.spoiler:
                description = self._make_spoiler_text(self.description)
                embed_args["description"] = description
            else:
                embed_args["description"] = self.description
            self._type = self.MessageTypes.TEXT_EMBED
        embed = discord.Embed(**embed_args)

        if self.image_url:
            embed.set_image(url=self.image_url)
            self._type = self.MessageTypes.IMAGE_EMBED
        output["embed"] = embed

    def _upload_image_embed(self, output):
        embed = discord.Embed(title=self.title)
        image_type = "gif"  # TODO Figure out libmagic issues?
        # image_type = magic.from_buffer(self.image, mime=True)
        # # Example output: image/gif
        # try:
        #     image_type = image_type.split('/')[1]
        # except IndexError:
        #     image_type = 'jpg' # Fallback to jpg?
        # Discord can't use underscores in embeds?
        filename = f"{self.title}.{image_type}".replace("_", "").replace(" ", "")
        output["file"] = discord.File(BytesIO(self.image), filename=filename)
        embed.set_image(url=f"attachment://{filename}")
        output["embed"] = embed

    @staticmethod
    def _make_spoiler_text(text):
        safe_text = text.replace(r"|", r"\|")
        spoiler = f"||{safe_text}||"
        return spoiler


class AbstractProcessor(abc.ABC):
    """Base processor for all video fetches"""

    DISCORD_MAX_FILESIZE = 8388119
    DISCORD_MAX_PREVIEW = 51200000
    # 200Kb/s (25.6KB/s) is the minimum size we'll try.
    MAX_LENGTH = DISCORD_MAX_FILESIZE / 25600

    @property
    @abc.abstractmethod
    def regex_checks(self):
        """A list of compiled regex"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"owldyn.vidlinks.processor.{self.__class__.__name__}")
        self.sydl = None
        self.shrinked_file = None
        self.ffmpeg = Ffmpeg()
        self._video_info = None
        self._video_duration = None

    def __enter__(self):
        self.sydl = TemporaryYoutubeDL()
        self.sydl.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sydl.__exit__(exc_type, exc_value, traceback)

    class InvalidURL(Exception):
        """Exception to raise when the url isn't valid."""

    class VideoTooLarge(Exception):
        """Exception to raise when the file can't be shrunk enough."""

    @property
    def video_info(self):
        """Video info from ffprobe"""
        if self._video_info:
            return self._video_info
        self._video_info = self.ffmpeg.get_information(self.sydl.downloaded_file)
        return self._video_info

    @property
    def video_duration(self):
        """Video duration from video info"""
        if self._video_duration:
            return self._video_duration
        self._video_duration = self.video_info.get("format", {}).get("duration")
        return self._video_duration

    @abc.abstractmethod
    def verify_link(self, url, audio, **kwargs):
        """Verifies the url is valid."""

    def attempt_shrink(self, recursion_depth: int = 0):
        """Uses ffmpeg to attempt to shrink the video to fit within Discord's file size limits
        Recursively reduces the dimensions by half,
        then uses a higher CRF until the file is below the limit"""
        if self.video_duration and float(self.video_duration) > self.MAX_LENGTH:
            # We're gonna try to shrink it even if we can't get the duration
            raise self.VideoTooLarge("Video is too long to shrink without extreme quality loss.")
        if recursion_depth >= 4:
            raise self.VideoTooLarge(
                f"Tried to shink a total of {recursion_depth} times but it was still too large!"
            )
        self.logger.debug("file_size before %s = %s", recursion_depth, self.sydl.file_size)
        self.ffmpeg.shrink_video(self.sydl.downloaded_file)
        if self.sydl.file_size > self.DISCORD_MAX_FILESIZE:
            self.logger.debug("file_size after1 %s = %s", recursion_depth, self.sydl.file_size)
            self.ffmpeg.lower_quality(self.sydl.downloaded_file)
            self.logger.debug("file_size after2 %s = %s", recursion_depth, self.sydl.file_size)
            if self.sydl.file_size > self.DISCORD_MAX_FILESIZE:
                # Recurse if too big still
                self.attempt_shrink(recursion_depth + 1)
        return recursion_depth

    def check_audio(self, remove_audio: bool):
        """Removes audio if requested.
        Will generate a silent audio track if one doesn't exist,
        as the Discord client seems to dislike no audio on videos.

        Args:
            remove_audio (bool): Whether to remove the audio
        """
        if not remove_audio:
            has_audio = self.ffmpeg.check_for_audio(self.video_info)
            if not has_audio:
                remove_audio = True

        if remove_audio:
            self.ffmpeg.replace_audio(self.sydl.downloaded_file)

    def normalize_file(self):
        """Normalize file for any issues caused by how we use yt-dlp"""
        self.ffmpeg.normalize_file(self.sydl.downloaded_file)

    def _generic_video_dl(self, url: str, audio: bool = False, **kwargs):
        self.sydl.download_video(url)
        self.normalize_file()
        self.check_audio(audio)
        if self.sydl.file_size > self.DISCORD_MAX_FILESIZE:
            self.logger.info("File is larger than discord max filesize, attempting shrinkage.")
            if self.attempt_shrink() is not False:
                self.sydl.downloaded_file.seek(0)
                return BytesIO(self.sydl.downloaded_file.read())
            # Fallback just in case? should never hit this though.
            raise self.VideoTooLarge()

        self.sydl.downloaded_file.seek(0)
        return BytesIO(self.sydl.downloaded_file.read())

    async def process_url(
        self, url: str, audio: bool = False, **kwargs
    ) -> Dict[str, MessageBuilder]:
        """Processes the URL given and returns the processed information.

        Args:
            url (str): The url of the video
            audio (bool, optional): Whether to remove the audio. Defaults to False.

        Raises:
            self.VideoTooLarge: If the video is too large to reduce to below DISCORD_MAX_SIZE

        Returns:
            dict: all of the returns
        """
        return self.verify_link(url, audio, **kwargs)
