import subprocess
import tempfile
import json

class Ffmpeg:
    def _run_process_on_file(self, command, file):
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
            # Seek the file to prep it for piping
            file.seek(0)
            return process.communicate(input=file.read())

    def get_information(self, file: tempfile.SpooledTemporaryFile):
        """Gets a json of the information of the file."""
        command = ['ffprobe']
        args = ['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-']
        command.extend(args)
        
        json_string = self._run_process_on_file(command, file)[0].decode('utf-8')
        return json.loads(json_string)

    def check_for_audio(self, file_information: dict = None) -> bool:
        """Checks if there is audio in the file"""
        streams = file_information.get('streams', [])
        for stream in streams:
            if stream.get('codec_type', '') == 'audio':
                return True
        return False

    def replace_audio(self, file: tempfile.SpooledTemporaryFile):
        """Replaces the file's audio with silent audio. Works even if there's no audio track.
        Modifies the file object in place."""
        command = ['ffmpeg']
        args = ['-i', '-', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', '-f', 'mp4', '-']
        command.extend(args)

        removed_audio = self._run_process_on_file(command, file)[0]
        # Erase the file and replace it with the new file.
        file.seek(0)
        file.truncate()
        file.write(removed_audio)
