"""Load app configuration from config.yaml (with config.example.yaml as fallback)."""
import os
import yaml

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
_EXAMPLE_PATH = os.path.join(os.path.dirname(__file__), "config.example.yaml")


def load_config() -> dict:
    path = _CONFIG_PATH if os.path.exists(_CONFIG_PATH) else _EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    passphrase_env = cfg.get("pgp", {}).get("passphrase_env")
    cfg["pgp"]["passphrase"] = os.environ.get(passphrase_env, "") if passphrase_env else ""
    return cfg


def save_config(updates: dict) -> None:
    """שומר עדכונים (sftp/edi וכו') לקובץ config.yaml, ומעדכן את ה-singleton בזיכרון.

    updates הוא dict חלקי, למשל {"sftp": {...}, "edi": {...}}.
    לא נשמר passphrase בפועל - הוא תמיד מגיע מ-env var (ר' passphrase_env).
    """
    path = _CONFIG_PATH if os.path.exists(_CONFIG_PATH) else _EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        on_disk = yaml.safe_load(f) or {}

    for section, values in updates.items():
        on_disk.setdefault(section, {})
        on_disk[section].update(values)
        config.setdefault(section, {})
        config[section].update(values)

    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(on_disk, f, allow_unicode=True, sort_keys=False)


config = load_config()
