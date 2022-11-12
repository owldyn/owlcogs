import abc
import logging

from .libraries.memory_ydl import SpooledYoutubeDL
import tempfile
DISCORD_MAX_FILESIZE = 8388119

class AbstractProcessor(abc.ABC):
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"owldyn.vidlinks.processor.{self.__class__.__name__}")
        self.sydl = None
        self.shrinked_file = None

    def __enter__(self):
        self.sydl = SpooledYoutubeDL()
        self.shrinked_file = tempfile.SpooledTemporaryFile()
        self.sydl.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sydl.__exit__(exc_type, exc_value, traceback)
        self.shrinked_file.close()

    class InvalidURL(Exception):
        """Exception to raise when the url isn't valid."""

    class VideoTooLarge(Exception):
        """Exception to raise when the file can't be shrunk enough."""

    @abc.abstractmethod
    @property
    def ydl_opts(self):
        """Options to pass to yt-dlp"""

    @abc.abstractmethod
    def verify_link(self, url):
        """Verifies the url is valid."""

    def attempt_shrink(self):
        """Uses ffmpeg to attempt to shrink the video to fit within Discord's file size limits"""
        raise NotImplementedError()

    def check_audio(self, audio: bool):
        """Uses ffmpeg to check if the audio should be removed, or remove it if requested
        
        Args:
            audio (bool): Whether to remove the audio
        """
        raise NotImplementedError()

    def process_url(self, url: str, audio: bool = False):
        """Processes the URL given and returns the video file.

        Args:
            url (str): The url of the video
            audio (bool, optional): Whether to remove the audio. Defaults to False.

        Raises:
            self.VideoTooLarge: If the video is too large to reduce to below DISCORD_MAX_SIZE

        Returns:
            video: a SpooledTemporaryFile of the video
        """
        self.verify_link(url)
        self.sydl.download_video(url)
        self.check_audio(audio)
        if self.sydl.file_size < DISCORD_MAX_FILESIZE:
            self.logger.info('File is larger than discord max filesize, attempting shrinkage.')
            if self.attempt_shrink():
                return self.shrinked_file
            raise self.VideoTooLarge()

        return self.sydl.downloaded_file
