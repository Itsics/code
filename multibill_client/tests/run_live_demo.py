"""End-to-end demo: real GPG encryption + a real local SFTP server (paramiko
protocol), running the actual (non-mocked) sftp_client.py / decryption.py /
edi_parser.py code paths - nothing about the app itself is faked here.

Simulates: a bank sends an encrypted account/payment file over SFTP.

Note: uses an isolated, throwaway GNUPGHOME so this never touches your real
GPG keyring.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gnupg  # noqa: E402

from mock_sftp_server import MockSFTPServer  # noqa: E402

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "bank_statement_sample.edi")

REMOTE_DIR = tempfile.mkdtemp(prefix="multibill_demo_remote_")
GNUPG_HOME = tempfile.mkdtemp(prefix="multibill_demo_gnupg_")
WORKDIR = tempfile.mkdtemp(prefix="multibill_demo_work_")
PASSPHRASE = "demo-passphrase"


def _gpg_home_arg(path: str) -> str:
    """Windows MSYS-built gpg.exe (e.g. Git for Windows) mis-parses native
    'C:\\...' paths passed as --homedir / GNUPGHOME, so convert to the
    '/c/...' form it expects. No-op on other platforms."""
    if os.name != "nt":
        return path
    drive, rest = os.path.splitdrive(path)
    if not drive:
        return path.replace(os.sep, "/")
    return f"/{drive[0].lower()}/{rest.replace(os.sep, '/').lstrip('/')}"


def main():
    # 1. Generate a fresh PGP keypair (stands in for the bank's real key) and
    #    use it to encrypt the sample bank file, "as the bank would".
    gpg = gnupg.GPG(options=["--pinentry-mode", "loopback"])
    gpg.gnupghome = _gpg_home_arg(GNUPG_HOME)  # bypass python-gnupg's native isdir() check

    key_input = gpg.gen_key_input(
        name_real="Multibill Demo",
        name_email="demo@multibill.local",
        passphrase=PASSPHRASE,
        key_type="RSA",
        key_length=2048,
    )
    key = gpg.gen_key(key_input)
    if not key.fingerprint:
        raise RuntimeError(f"PGP key generation failed: {key.stderr}")

    private_key_path = os.path.join(WORKDIR, "private_demo.asc")
    with open(private_key_path, "w", encoding="utf-8") as f:
        f.write(gpg.export_keys(key.fingerprint, secret=True, passphrase=PASSPHRASE))

    with open(SAMPLE_PATH, "rb") as f:
        encrypted = gpg.encrypt_file(f, recipients=[key.fingerprint], always_trust=True)
    if not encrypted.ok:
        raise RuntimeError(f"Encryption failed: {encrypted.status}")

    remote_filename = "bank_statement_2026-07-03.edi.gpg"
    with open(os.path.join(REMOTE_DIR, remote_filename), "wb") as f:
        f.write(encrypted.data)
    print(f"[1/4] Encrypted sample bank file with a fresh demo PGP key -> {remote_filename}")

    # 2. Start a real local SFTP server (actual SSH/SFTP protocol) serving REMOTE_DIR.
    server = MockSFTPServer(root_dir=REMOTE_DIR, username="demo_user", password="demo_pass").start()
    print(f"[2/4] Mock SFTP server listening on 127.0.0.1:{server.port} (user=demo_user / pass=demo_pass)")

    try:
        # decryption.py's GPG() call has no explicit homedir -> it reads GNUPGHOME
        # from the environment, so point that at our throwaway keyring too.
        os.environ["GNUPGHOME"] = _gpg_home_arg(GNUPG_HOME)

        # 3. Point the REAL app config at the mock server + demo PGP key.
        import config as config_module  # noqa: E402
        config_module.config["sftp"] = {
            "host": "127.0.0.1",
            "port": server.port,
            "username": "demo_user",
            "password": "demo_pass",
            "private_key_path": "",
            "remote_dir": "/",
            "local_dir": os.path.join(WORKDIR, "downloads"),
        }
        config_module.config["pgp"]["private_key_path"] = private_key_path
        config_module.config["pgp"]["passphrase"] = PASSPHRASE
        config_module.config["pgp"]["decrypted_dir"] = os.path.join(WORKDIR, "decrypted")
        # Deliberately NOT overriding database.url: this writes into the same
        # multibill.db the running `uvicorn main:app` process uses, so the
        # result shows up in the browser UI (http://localhost:8000) too.

        import models  # noqa: E402
        models.init_db()

        import main  # noqa: E402  (real SFTPClient + real decrypt_file, nothing mocked)

        print("[3/4] Running the real pull cycle (real SFTP + real PGP decryption + EDI parsing)...")
        main.run_pull_cycle()

        session = models.get_session()
        records = session.query(models.FileRecord).all()
        for r in records:
            print(f"    {r.filename}: {r.status} | {r.parsed_summary or r.error_message}")
        demo_record = session.query(models.FileRecord).filter_by(filename=remote_filename).first()
        session.close()

        assert demo_record is not None, f"{remote_filename} was not recorded in the DB"
        assert demo_record.status == "parsed", f"Expected parsed, got {demo_record.status}: {demo_record.error_message}"
        print("[4/4] SUCCESS - real SFTP + real PGP + EDI parsing all worked end-to-end.")

    finally:
        server.stop()
        shutil.rmtree(WORKDIR, ignore_errors=True)
        shutil.rmtree(REMOTE_DIR, ignore_errors=True)
        shutil.rmtree(GNUPG_HOME, ignore_errors=True)


if __name__ == "__main__":
    main()
