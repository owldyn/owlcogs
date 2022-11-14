import json
import subprocess
import tempfile
from enum import Enum


class Ffmpeg:
    @staticmethod
    def _run_process_on_file(command, file):
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
            # Seek the file to prep it for piping
            file.seek(0)
            return process.communicate(input=file.read())

    def get_information(self, file: tempfile.SpooledTemporaryFile) -> dict:
        """Gets a json of the information of the file."""
        args = ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-']
        json_string = self.run_ffmpeg_command_on_file(self.Commands.FFPROBE, args, file)[0].decode('utf-8')
        return json.loads(json_string)

    @staticmethod
    def check_for_audio(file_information: dict) -> bool:
        """Checks if there is audio in the file from the given file information"""
        streams = file_information.get('streams', [])
        for stream in streams:
            if stream.get('codec_type', '') == 'audio':
                return True
        return False

    class Commands(Enum):
        """The commands to run ffmpeg with"""
        FFMPEG = ['ffmpeg']
        FFPROBE = ['ffprobe']

    def run_ffmpeg_command_on_file(self, command: Commands, 
                                   args: list, file: tempfile.SpooledTemporaryFile) -> tuple:
        """Runs the command with the given args on the given file.

        Args:
            command (Commands): The command to run
            args (list): The args to add to the command
            file (tempfile.SpooledTemporaryFile): The file to run it on.

        Returns:
            tuple: the return from subprocess.popen.communicate
        """
        command = command.value
        command.extend(args)
        return self._run_process_on_file(command, file)

    @staticmethod
    def _replace_file(original_file: tempfile.SpooledTemporaryFile, new_data):
        original_file.seek(0)
        original_file.truncate()
        original_file.write(new_data)

    def replace_audio(self, file: tempfile.SpooledTemporaryFile):
        """Replaces the file's audio with silent audio. Works even if there's no audio track.
        Modifies the file object in place."""
        args = ['-i', '-', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', '-f', 'mp4', '-']

        removed_audio = self.run_ffmpeg_command_on_file(self.Commands.FFMPEG ,args, file)[0]
        # Erase the file and replace it with the new file.
        self._replace_file(file, removed_audio)

    def shrink_video(self, file: tempfile.SpooledTemporaryFile):
        """Lowers the quality of the video by halving the resolution on both axis."""
        args = ['ffmpeg', '-i', '-', '-crf', '24', '-vf',
                'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', '-f', 'mp4', '-']

        smaller_video = self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)
        self._replace_file(file, smaller_video)

    def lower_quality(self, file: tempfile.SpooledTemporaryFile):
        """Lowers the quality of the video by using crf 28."""
        args = ['ffmpeg', '-i', '-', '-preset',
                'veryfast', '-crf', '28', '-c:a', 'copy', '-f', 'mp4', '-']

        smaller_video = self.run_ffmpeg_command_on_file(self.Commands.FFMPEG, args, file)
        self._replace_file(file, smaller_video)
