"""פענוח PGP - stub ראשוני.

TODO: יש להתאים לשיטת ההצפנה בפועל מול הבנק (symmetric / public-key,
gpg vs. פורמט אחר). כרגע מיושם עם python-gnupg, בהנחת מפתח פרטי + passphrase.
"""
import os
import gnupg

from config import config


def decrypt_file(input_path: str, output_dir: str = None) -> str:
    """מפענח קובץ PGP ומחזיר את הנתיב לקובץ המפוענח."""
    pgp_cfg = config["pgp"]
    output_dir = output_dir or pgp_cfg.get("decrypted_dir", "./decrypted")
    os.makedirs(output_dir, exist_ok=True)

    # pinentry-mode loopback: מאפשר להעביר passphrase ישירות בלי צורך בפרומפט
    # אינטראקטיבי (pinentry) - הכרחי כשרצים כשירות/שרת בלי TTY.
    gpg = gnupg.GPG(options=["--pinentry-mode", "loopback"])
    key_path = pgp_cfg.get("private_key_path")
    if key_path and os.path.exists(key_path):
        with open(key_path, "rb") as key_file:
            gpg.import_keys(key_file.read())

    filename = os.path.basename(input_path)
    output_path = os.path.join(output_dir, filename.rsplit(".gpg", 1)[0] if filename.endswith(".gpg") else filename + ".dec")

    with open(input_path, "rb") as f:
        status = gpg.decrypt_file(f, passphrase=pgp_cfg.get("passphrase") or None, output=output_path)

    if not status.ok:
        raise RuntimeError(f"PGP decryption failed for {filename}: {status.status}")

    return output_path
