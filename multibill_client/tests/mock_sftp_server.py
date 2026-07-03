"""Local, in-process SFTP server (real paramiko protocol) for demoing/testing
sftp_client.py without a real bank server. Serves a local directory over
actual SSH/SFTP on 127.0.0.1 with password auth.
"""
import os
import socket
import threading

import paramiko


class _AuthServer(paramiko.ServerInterface):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    # Deliberately no check_channel_subsystem_request override: the base
    # ServerInterface implementation looks up Transport.set_subsystem_handler
    # and actually starts the handler thread. Overriding it to just "return
    # True" (a common copy-paste mistake) accepts the subsystem request
    # without ever launching the SFTP handler, causing the client to hang.


class _RootedSFTPServer(paramiko.SFTPServerInterface):
    """Serves ROOT (set per-instance from MockSFTPServer) as the SFTP root."""

    ROOT = "."

    def _full(self, path):
        path = self.canonicalize(path)
        return os.path.join(self.ROOT, path.lstrip("/"))

    def list_folder(self, path):
        full = self._full(path)
        try:
            out = []
            for fname in os.listdir(full):
                attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(full, fname)))
                attr.filename = fname
                out.append(attr)
            return out
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        full = self._full(path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(full))
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    lstat = stat

    def open(self, path, flags, attr):
        full = self._full(path)
        try:
            fd = os.open(full, flags | getattr(os, "O_BINARY", 0))
            f = os.fdopen(fd, "rb")
        except OSError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        handle = paramiko.SFTPHandle(flags)
        handle.readfile = f
        handle.writefile = f
        return handle


class MockSFTPServer:
    """Starts a background thread serving `root_dir` over real SFTP on localhost."""

    def __init__(self, root_dir, username="demo_user", password="demo_pass", host="127.0.0.1"):
        self.root_dir = os.path.abspath(root_dir)
        self.username = username
        self.password = password
        self.host_key = paramiko.RSAKey.generate(2048)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind((host, 0))
        self._sock.listen(5)
        self.port = self._sock.getsockname()[1]

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _serve_forever(self):
        self._sock.settimeout(1.0)
        while not self._stop_event.is_set():
            try:
                client_sock, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()

    def _handle_client(self, client_sock):
        transport = paramiko.Transport(client_sock)
        transport.add_server_key(self.host_key)
        _RootedSFTPServer.ROOT = self.root_dir
        transport.set_subsystem_handler("sftp", paramiko.SFTPServer, _RootedSFTPServer)
        server = _AuthServer(self.username, self.password)
        try:
            transport.start_server(server=server)
            channel = transport.accept(10)
            if channel is None:
                return
            while transport.is_active() and not self._stop_event.is_set():
                threading.Event().wait(0.2)
        except (paramiko.SSHException, OSError):
            pass
        finally:
            transport.close()

    def stop(self):
        self._stop_event.set()
        try:
            self._sock.close()
        except OSError:
            pass
