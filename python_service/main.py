#!/usr/bin/env python3
"""
MP3 Service - Audio File Processor
Main entry point for the application.
"""

import sys
import time
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.logger import setup_logger
from src.processor import AudioProcessor


class MP3Service:
    """Main service class for audio processing."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the MP3 service.

        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        self.logger = setup_logger(
            "MP3Service",
            log_file=self.config.log_file,
            level=self.config.log_level
        )
        self.processor = AudioProcessor(self.config)
        self.running = False

    def start(self) -> None:
        """Start the service."""
        self.logger.info("")
        self.logger.info("=" * 63)
        self.logger.info(f" -- MP3 Service started -- {AudioProcessor.VERSION}")
        self.logger.info("=" * 63)
        self.logger.info(f"Base Path: {self.config.base_path}")
        self.logger.info(f"Local Path: {self.config.local_path}")
        self.logger.info(f"Poll Interval: {self.config.poll_interval} seconds")
        self.logger.info(f"Network Share: {'Enabled' if self.config.include_share else 'Disabled'}")
        if self.config.include_share and self.config.network_path:
            self.logger.info(f"Network Path: {self.config.network_path}")
        self.logger.info("")

        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Run initial processing
        try:
            self.processor.process_all()
        except Exception as e:
            self.logger.error(f"Error during initial processing: {e}")

        # Main polling loop
        while self.running:
            try:
                time.sleep(self.config.poll_interval)
                self.logger.info("")
                self.logger.info("Polling for new files...")
                self.processor.process_all()
            except Exception as e:
                self.logger.error(f"Error during polling cycle: {e}")

    def stop(self) -> None:
        """Stop the service."""
        self.logger.info("")
        self.logger.info("=" * 63)
        self.logger.info("MP3 Service stopping...")
        self.logger.info("=" * 63)
        self.running = False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()


def main():
    """Main entry point."""
    # Check for config file path argument
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    # Check if config file exists
    if not Path(config_path).exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Please create a config.json file or specify a valid path.")
        print(f"Usage: python {sys.argv[0]} [config_path]")
        sys.exit(1)

    try:
        service = MP3Service(config_path)
        service.start()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
