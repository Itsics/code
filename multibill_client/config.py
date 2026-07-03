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


config = load_config()
