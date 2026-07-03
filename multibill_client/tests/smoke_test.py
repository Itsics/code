"""Smoke test for the full pull cycle, without real SFTP/PGP credentials.

Fakes SFTPClient (reads from tests/fixtures/remote instead of a real server)
and decrypt_file (just copies the "encrypted" fixture as-is, since it's plain
text), then runs the real run_pull_cycle() / edi_parser / models pipeline.
"""
import os
import shutil
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

FIXTURES_REMOTE = os.path.join(os.path.dirname(__file__), "fixtures", "remote")
WORKDIR = tempfile.mkdtemp(prefix="multibill_smoke_")

import config as config_module  # noqa: E402
config_module.config["database"]["url"] = f"sqlite:///{WORKDIR}/smoke.db"

import models  # noqa: E402
models.init_db()

import main  # noqa: E402


class FakeSFTPClient:
    def __init__(self, cfg=None):
        self.remote_dir = FIXTURES_REMOTE
        self.local_dir = os.path.join(WORKDIR, "downloads")
        os.makedirs(self.local_dir, exist_ok=True)

    def connect(self):
        return self

    def list_remote_files(self):
        return os.listdir(self.remote_dir)

    def download_file(self, filename):
        src = os.path.join(self.remote_dir, filename)
        dst = os.path.join(self.local_dir, filename)
        shutil.copyfile(src, dst)
        return dst

    def close(self):
        pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()


def fake_decrypt_file(input_path, output_dir=None):
    output_dir = output_dir or os.path.join(WORKDIR, "decrypted")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    out_name = filename[:-4] if filename.endswith(".gpg") else filename + ".dec"
    dst = os.path.join(output_dir, out_name)
    shutil.copyfile(input_path, dst)
    return dst


main.SFTPClient = FakeSFTPClient
main.decrypt_file = fake_decrypt_file

main.run_pull_cycle()

session = models.get_session()
records = session.query(models.FileRecord).all()
for r in records:
    print(r.filename, r.status, r.parsed_summary, r.error_message)

api_files = main.list_files()
print("api/files:", api_files)

session.close()

assert len(records) == 1, f"Expected 1 record, got {len(records)}"
assert records[0].status == "parsed", f"Expected parsed, got {records[0].status}: {records[0].error_message}"

shutil.rmtree(WORKDIR, ignore_errors=True)
print("SMOKE TEST PASSED")
