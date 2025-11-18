"""Configuration management for MP3 Service."""

import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Handles loading and accessing configuration settings."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.

        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

        # Validate required fields
        self._validate()

    def _validate(self) -> None:
        """Validate that required configuration fields exist."""
        required_fields = [
            'base_path',
            'local_path',
            'poll_interval',
        ]

        missing_fields = [field for field in required_fields if field not in self._config]
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    @property
    def base_path(self) -> Path:
        """Get base path for file monitoring."""
        return Path(self._config['base_path'])

    @property
    def local_path(self) -> Path:
        """Get local path for processed files."""
        return Path(self._config['local_path'])

    @property
    def network_path(self) -> Path:
        """Get network path for sharing files."""
        path = self._config.get('network_path')
        return Path(path) if path else None

    @property
    def desktop_path(self) -> Path:
        """Get desktop path."""
        path = self._config.get('desktop_path')
        return Path(path) if path else None

    @property
    def poll_interval(self) -> int:
        """Get polling interval in seconds."""
        return int(self._config['poll_interval'])

    @property
    def include_share(self) -> bool:
        """Check if network share copying is enabled."""
        return self._config.get('include_share', False)

    @property
    def supported_extensions(self) -> tuple:
        """Get tuple of supported audio file extensions."""
        return tuple(self._config.get('supported_extensions', [
            '.mp3', '.m4a', '.wav', '.aif', '.aiff', '.flac'
        ]))

    @property
    def bpm_range(self) -> tuple:
        """Get acceptable BPM range as (min, max)."""
        bpm_config = self._config.get('bpm_range', {'min': 65, 'max': 135})
        return (bpm_config['min'], bpm_config['max'])

    @property
    def log_file(self) -> Path:
        """Get log file path."""
        return Path(self._config.get('log_file', 'mp3_service.log'))

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config.get('log_level', 'INFO')

    @property
    def backup_before_delete(self) -> bool:
        """Check if files should be backed up before deletion."""
        return self._config.get('backup_before_delete', False)

    @property
    def backup_path(self) -> Path:
        """Get backup path for original files."""
        path = self._config.get('backup_path')
        return Path(path) if path else None

    @property
    def file_stability_wait(self) -> int:
        """Get seconds to wait for file stability (polling mode)."""
        return int(self._config.get('file_stability_wait', 2))

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(config_path='{self.config_path}')"


def create_default_config() -> Dict[str, Any]:
    """
    Create a default configuration dictionary.

    Returns:
        Default configuration dictionary
    """
    return {
        "base_path": str(Path.home() / "Music" / "Incoming"),
        "local_path": str(Path.home() / "Music" / "Processed"),
        "network_path": "",
        "desktop_path": "",
        "poll_interval": 40,
        "include_share": False,
        "supported_extensions": [
            ".mp3",
            ".m4a",
            ".wav",
            ".aif",
            ".aiff",
            ".flac"
        ],
        "bpm_range": {
            "min": 65,
            "max": 135
        },
        "backup_before_delete": False,
        "backup_path": "",
        "file_stability_wait": 2,
        "log_file": "mp3_service.log",
        "log_level": "INFO"
    }
