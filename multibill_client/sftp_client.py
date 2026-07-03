"""חיבור ומשיכת קבצים חדשים מ-SFTP.

TODO (קריטי לאבטחה): כרגע נעשה שימוש ב-AutoAddPolicy שמקבל כל host key
בלי אימות. יש להחליף לאימות מול known_hosts (client.load_host_keys /
client.set_missing_host_key_policy(paramiko.RejectPolicy)) לפני production.

TODO: אין כרגע retry/timeout handling למקרים של ניתוק, timeout או הורדה
חלקית של קובץ.
"""
import os
import paramiko

from config import config


class SFTPClient:
    def __init__(self, cfg: dict = None):
        cfg = cfg or config["sftp"]
        self.host = cfg["host"]
        self.port = cfg.get("port", 22)
        self.username = cfg["username"]
        self.password = cfg.get("password") or None
        self.private_key_path = cfg.get("private_key_path") or None
        self.remote_dir = cfg["remote_dir"]
        self.local_dir = cfg["local_dir"]
        os.makedirs(self.local_dir, exist_ok=True)

        self._ssh = None
        self._sftp = None

    def connect(self):
        self._ssh = paramiko.SSHClient()
        # TODO: להחליף ב-known_hosts אמיתי במקום קבלה אוטומטית של host key
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {"hostname": self.host, "port": self.port, "username": self.username}
        if self.private_key_path:
            connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(self.private_key_path)
        else:
            connect_kwargs["password"] = self.password

        self._ssh.connect(**connect_kwargs)
        self._sftp = self._ssh.open_sftp()
        return self

    def list_remote_files(self) -> list[str]:
        return self._sftp.listdir(self.remote_dir)

    def download_file(self, filename: str) -> str:
        remote_path = f"{self.remote_dir}/{filename}"
        local_path = os.path.join(self.local_dir, filename)
        self._sftp.get(remote_path, local_path)
        return local_path

    def close(self):
        if self._sftp:
            self._sftp.close()
        if self._ssh:
            self._ssh.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
