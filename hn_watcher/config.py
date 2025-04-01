import os
from pathlib import Path
from typing import Any, Dict

import toml


def find_config_file() -> str:
    """
    Find the configuration file in standard locations.

    Look for config in the following locations (in order):
    1. ./hn_watcher.toml (current directory)
    2. ~/.config/hn_watcher/config.toml (user config directory)
    3. /etc/hn_watcher/config.toml (system config directory)

    Returns:
        Path to the first config file found, or None if no config file exists
    """
    # Check current directory
    current_dir = Path("./hn_watcher.toml")
    if current_dir.exists():
        return str(current_dir)

    # Check user config directory
    user_config = Path.home() / ".config" / "hn_watcher" / "config.toml"
    if user_config.exists():
        return str(user_config)

    # Check system config directory
    system_config = Path("/etc/hn_watcher/config.toml")
    if system_config.exists():
        return str(system_config)

    return ""


def load_config(config_path: str = "") -> Dict[str, Any]:
    """
    Load configuration from a TOML file.

    Args:
        config_path: Path to the configuration file. If not provided,
                    the function will search for a config file in standard locations.

    Returns:
        Dictionary with configuration values
    """
    if not config_path:
        config_path = find_config_file()

    # Default configuration
    default_config = {
        "database": {"path": "hn_comments.db"},
        "rabbitmq": {
            "host": "localhost",
            "exchange": "hackernews",
            "exchange_type": "topic",
            "durable": True,
        },
        "api": {
            "request_delay": 0.1,
            "base_url": "https://hacker-news.firebaseio.com/v0",
        },
    }

    # If config file exists, load it and merge with defaults
    if config_path and os.path.exists(config_path):
        try:
            user_config = toml.load(config_path)

            # Merge with defaults (simple implementation)
            for section in default_config:
                if section in user_config:
                    default_config[section].update(user_config[section])  # type: ignore
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")

    return default_config
