import logging
from datetime import datetime
from io import StringIO

import paramiko


class ZFSSSHHandler:
    def __init__(self, node: dict):
        self.host = node["host"]
        self._node = node
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.priv_key = paramiko.RSAKey.from_private_key(StringIO(node["key"]))
        self.log = logging.getLogger("pterodactyl.zfs_ssh_handler")

    def connect(self):
        self.client.connect(
            self.host, pkey=self.priv_key, username=self._node["username"]
        )

    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode() + stderr.read().decode()

    def close(self):
        self.client.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return

    def zfs_snapshot(self):
        # Tag snapshot in format autosnap_YYYY-MM-DD_HH:MM:SS_manual
        tag = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        dataset = self._node["dataset"]
        full = f"{dataset}@autosnap_{tag}_manual"
        self.log.info(full)
        command = f"sudo zfs snapshot {full} -r"
        self.execute(command)
        return self.execute(f"zfs list -t snapshot | grep {full}")
