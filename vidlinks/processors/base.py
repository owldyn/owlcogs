import abc
import logging
import tempfile
from io import BytesIO

from .libraries.ffmpeg import Ffmpeg
from .libraries.memory_ydl import SpooledYoutubeDL

DISCORD_MAX_FILESIZE = 8388119
MAX_LENGTH = DISCORD_MAX_FILESIZE / 25600 # 200Kb/s (25.6KB/s) is the minimum size we'll try.

class AbstractProcessor(abc.ABC):
    """Base processor for all video fetches"""
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"owldyn.vidlinks.processor.{self.__class__.__name__}")
        self.sydl = None
        self.shrinked_file = None
        self.ffmpeg = Ffmpeg()
        self._video_info = None
        self._video_duration = None

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
        self._video_duration = self.video_info.get('format', {}).get('duration')
        return self._video_duration

    @abc.abstractmethod
    def verify_link(self, url):
        """Verifies the url is valid."""

    def attempt_shrink(self, recursion_depth: int = 0):
        """Uses ffmpeg to attempt to shrink the video to fit within Discord's file size limits
        Recursively reduces the dimensions by half,
        then uses a higher CRF until the file is below the limit"""
        if self.video_duration and self.video_duration > MAX_LENGTH:
            # We're gonna try to shrink it even if we can't get the duration
            raise self.VideoTooLarge('Video is too long to shrink without extreme quality loss.')
        if recursion_depth >= 4:
            raise self.VideoTooLarge(f'Tried to shink a total of {recursion_depth} times but it was still too large!')
        self.logger.debug('file_size before %s = %s', recursion_depth, self.sydl.file_size)
        self.ffmpeg.shrink_video(self.sydl.downloaded_file)
        if self.sydl.file_size > DISCORD_MAX_FILESIZE:
            self.logger.debug('file_size after1 %s = %s', recursion_depth, self.sydl.file_size)
            self.ffmpeg.lower_quality(self.sydl.downloaded_file)
            self.logger.debug('file_size after2 %s = %s', recursion_depth, self.sydl.file_size)
            if self.sydl.file_size > DISCORD_MAX_FILESIZE:
                self.attempt_shrink(recursion_depth+1) # Recurse if too big still
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
        if self.sydl.file_size > DISCORD_MAX_FILESIZE:
            self.logger.info('File is larger than discord max filesize, attempting shrinkage.')
            if self.attempt_shrink() is not False:
                self.sydl.downloaded_file.seek(0)
                return BytesIO(self.sydl.downloaded_file.read())
            raise self.VideoTooLarge()

        self.normalize_file()
        self.sydl.downloaded_file.seek(0)
        return BytesIO(self.sydl.downloaded_file.read())
