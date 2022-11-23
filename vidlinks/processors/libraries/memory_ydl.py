import os
import subprocess
import tempfile


class SpooledYoutubeDL:
    """Uses a SpooledTemporaryFile and yt-dlp to fetch 
    and expose a youtube file without downloading it."""
    def __init__(self) -> None:
        self.downloaded_file = None

    def __enter__(self):
        self.downloaded_file = tempfile.SpooledTemporaryFile()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.downloaded_file.close()

    def download_video(self, url: str, ydl_opts = None):
        """Download the file into self.downloaded_file

        Args:
            url (str): the url to download from
            ydl_opts (list, optional): Arguments to add to the yt-dlp command. Defaults to None.
        """
        base_command = ['yt-dlp']
        if ydl_opts is None:
            ydl_opts = []
        base_command.extend(ydl_opts)
        base_command.extend([url, '-o', '-'])

        download_command = subprocess.run(base_command, stdout=subprocess.PIPE, check=False)
        self.downloaded_file.write(download_command.stdout)

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
