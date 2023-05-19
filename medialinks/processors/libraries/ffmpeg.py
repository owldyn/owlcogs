import json
import subprocess
import tempfile
from enum import Enum
import logging

logger = logging.getLogger("owldyn.vidlinks.library.ffmpeg")


class Ffmpeg:
    ffmpeg_always_args = ["-y", "-f", "mp4"]

    def __init__(self) -> None:  # TODO Convert this to ask for the file to begin with.
        """Class for handling ffmpeg calls.
        Make one instance per video file!"""
        self._information = None

    @staticmethod
    def _run_process_on_file(command):
        # with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        #     # Seek the file to prep it for piping
        #     file.seek(0)
        #     info = process.communicate(input=file.read())
        logger.debug(f"Running ffmpeg command {command}")
        try:
            info = subprocess.run(command, capture_output=True, check=False)
            info.check_returncode()
        except Exception as exc:
            logger.error(info.stderr)
            raise exc
        return [info.stdout, info.stderr]

    def get_information(self, file: tempfile.NamedTemporaryFile) -> dict:
        """Gets a json of the information of the file."""
        if self._information is None:
            args = [
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file.name,
            ]
            json_string = self.run_ffprobe_command_on_file(self.Commands.FFPROBE, args)[
                0
            ].decode("utf-8")
            try:
                return json.loads(json_string)
            except json.JSONDecodeError as exc:
                raise self.FfmpegError(file) from exc
        return self._information

    @staticmethod
    def check_for_audio(file_information: dict) -> bool:
        """Checks if there is audio in the file from the given file information"""
        streams = file_information.get("streams", [])
        for stream in streams:
            if stream.get("codec_type", "") == "audio":
                return True
        return False

    class Commands(Enum):
        """The commands to run ffmpeg with"""

        FFMPEG = "ffmpeg"
        FFPROBE = "ffprobe"

    class FfmpegError(Exception):
        """Errors called in the FFMPEG library"""

        def __init__(self, file, *args: object) -> None:
            self.ffmpeg_response = Ffmpeg().run_ffprobe_command_on_file(
                Ffmpeg.Commands.FFPROBE, [file.name]
            )
            super().__init__(str(self.ffmpeg_response), *args)

    def run_ffmpeg_command_on_file(
        self, command: Commands, args: list, file: tempfile.NamedTemporaryFile
    ) -> tuple:
        """Runs the command with the given args on the given file.

        Args:
            command (Commands): The command to run
            args (list): The args to add to the command
            file (tempfile.NamedTemporaryFile): The file to run it on.

        Returns:
            tuple: the return from subprocess.popen.communicate
        """
        commandlist = [command.value]
        commandlist.extend(args)
        with tempfile.NamedTemporaryFile() as intermediate:
            if command == self.Commands.FFMPEG:
                commandlist.extend(self.ffmpeg_always_args)
                commandlist.append(intermediate.name)
            self._run_process_on_file(commandlist)
            self._replace_file(file, intermediate)

    def run_ffprobe_command_on_file(self, command: Commands, args: list) -> tuple:
        """Runs the command with the given args on the given file.

        Args:
            command (Commands): The command to run
            args (list): The args to add to the command
            file (tempfile.NamedTemporaryFile): The file to run it on.

        Returns:
            tuple: the return from subprocess.popen.communicate
        """
        commandlist = [command.value]
        commandlist.extend(args)
        if command == self.Commands.FFMPEG:
            commandlist.extend(self.ffmpeg_always_args)
        return self._run_process_on_file(commandlist)

    @staticmethod
    def _replace_file(
        original_file: tempfile.NamedTemporaryFile,
        new_file: tempfile.NamedTemporaryFile,
    ):
        new_file.seek(0)
        original_file.seek(0)
        original_file.truncate()
        original_file.write(new_file.read())

    def replace_audio(self, file: tempfile.NamedTemporaryFile):
        """Replaces the file's audio with silent audio. Works even if there's no audio track.
        Modifies the file object in place."""
        args = [
            "-i",
            file.name,
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-shortest",
        ]

        self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)

    def shrink_video(self, file: tempfile.NamedTemporaryFile):
        """Lowers the quality of the video by halving the resolution on both axis."""
        args = [
            "-i",
            file.name,
            "-crf",
            "24",
            "-vf",
            "scale=ceil(iw/4)*2:ceil(ih/4)*2",
            "-b:a",
            "128k",
        ]

        self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)

    def lower_quality(self, file: tempfile.NamedTemporaryFile):
        """Lowers the quality of the video by using crf 28."""
        args = ["-i", file.name, "-preset", "veryfast", "-crf", "28", "-b:a", "128k"]

        self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)

    def convert_to_mp4(self, file: tempfile.NamedTemporaryFile):
        """Converts file to mp4"""
        args = ["-i", file.name, "-c:v", "libx264", "-c:a", "copy"]
        self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)

    def normalize_file(self, file: tempfile.NamedTemporaryFile):
        """Runs the file through ffmpeg with copy codecs
        to fix any issues caused by the way we call yt-dlp."""
        args = ["-i", file.name, "-c:v", "copy", "-c:a", "copy"]

        self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)
