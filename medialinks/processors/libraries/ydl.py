import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


class TemporaryYoutubeDL:
    """Uses a NamedTemporaryFile and yt-dlp to fetch
    and expose a video file as a temporary file."""

    def __init__(self) -> None:
        self.downloaded_file = None

    def __enter__(self):
        self.downloaded_file = tempfile.NamedTemporaryFile()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.downloaded_file.close()

    def download_video(self, url: str, ydl_opts=None):
        """Download the file into self.downloaded_file

        Args:
            url (str): the url to download from
            ydl_opts (list, optional): Arguments to add to the yt-dlp command. Defaults to None.
        """
        base_command = ["yt-dlp"]

        if ydl_opts is None:
            ydl_opts = []
        base_command.extend(ydl_opts)
        base_command.extend(
            [url, "-o", f"{self.downloaded_file.name}.%(ext)s", "-j", "--no-simulate"]
        )
        try:
            download_command = subprocess.run(
                base_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
            )

            yt_dlp_output = json.loads(download_command.stdout)
            # Write the file contents from the downloaded file
            # since yt-dlp doesn't seem to allow you to strip file extensions.
            with open(
                Path(f'{self.downloaded_file.name}.{yt_dlp_output.get("ext")}'), "rb"
            ) as i_file:
                self.downloaded_file.seek(0)
                self.downloaded_file.write(i_file.read())

        finally:
            # Delete any files that shouldn't exist anymore.
            mid_files = glob.glob(f"{self.downloaded_file.name}.*")
            for file in mid_files:
                if (file_path := Path(file)).exists():
                    os.remove(file_path)

    @property
    def file_size(self):
        """Returns the filesize of the downloaded file."""
        # Get current seek to return to, just in case.
        current_seek = self.downloaded_file.tell()

        self.downloaded_file.seek(0, os.SEEK_END)
        filesize = self.downloaded_file.tell()

        # Return to it
        self.downloaded_file.seek(current_seek)

        return filesize
