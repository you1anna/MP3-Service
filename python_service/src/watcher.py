"""File system watcher for real-time audio file processing."""

import time
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from .config import Config
from .processor import AudioProcessor
from .logger import get_logger


class AudioFileHandler(FileSystemEventHandler):
    """Handles file system events for audio files."""

    def __init__(self, config: Config, processor: AudioProcessor):
        """
        Initialize audio file handler.

        Args:
            config: Configuration object
            processor: Audio processor instance
        """
        super().__init__()
        self.config = config
        self.processor = processor
        self.logger = get_logger(__name__)
        self.processing = set()  # Track files currently being processed

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if it's a supported audio file
        if file_path.suffix.lower() in self.config.supported_extensions:
            self._process_file_with_delay(file_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if it's a supported audio file and not already processed
        if (file_path.suffix.lower() in self.config.supported_extensions and
                str(file_path) not in self.processor.copied_files):
            self._process_file_with_delay(file_path)

    def _process_file_with_delay(self, file_path: Path):
        """
        Process file with delay to ensure it's fully written.

        Args:
            file_path: Path to file to process
        """
        # Skip if already processing
        file_str = str(file_path)
        if file_str in self.processing:
            return

        # Skip INCOMPLETE files
        if "INCOMPLETE~" in file_path.name:
            return

        # Skip if already processed
        if file_str in self.processor.copied_files:
            return

        try:
            self.processing.add(file_str)

            # Wait for file to be fully written (check file size stability)
            self._wait_for_file_ready(file_path)

            # Process the file
            self.logger.info("")
            self.logger.info("File detected by watcher:")
            self.processor.process_file(file_path)

        except Exception as e:
            self.logger.error(f"Error processing watched file {file_path}: {e}", exc_info=True)
        finally:
            if file_str in self.processing:
                self.processing.remove(file_str)

    def _wait_for_file_ready(self, file_path: Path, timeout: int = 30):
        """
        Wait for file to be fully written by checking size stability.

        Args:
            file_path: Path to file
            timeout: Maximum seconds to wait
        """
        last_size = -1
        wait_time = 0
        check_interval = 1  # Check every second

        while wait_time < timeout:
            try:
                if not file_path.exists():
                    time.sleep(check_interval)
                    wait_time += check_interval
                    continue

                current_size = file_path.stat().st_size

                # If size hasn't changed in last check, file is ready
                if current_size == last_size and current_size > 0:
                    return

                last_size = current_size
                time.sleep(check_interval)
                wait_time += check_interval

            except Exception as e:
                self.logger.debug(f"Error checking file readiness: {e}")
                time.sleep(check_interval)
                wait_time += check_interval

        # Timeout reached, proceed anyway
        self.logger.warning(f"File ready check timeout for {file_path.name}, processing anyway")


class FileWatcher:
    """Watches directories for new audio files."""

    def __init__(self, config: Config, processor: AudioProcessor):
        """
        Initialize file watcher.

        Args:
            config: Configuration object
            processor: Audio processor instance
        """
        self.config = config
        self.processor = processor
        self.logger = get_logger(__name__)
        self.observer: Optional[Observer] = None
        self.event_handler = AudioFileHandler(config, processor)

    def start(self):
        """Start watching for file changes."""
        try:
            self.observer = Observer()

            # Watch base directory recursively
            self.observer.schedule(
                self.event_handler,
                str(self.config.base_path),
                recursive=True
            )

            self.observer.start()
            self.logger.info(f"Watching directory: {self.config.base_path}")
            self.logger.info("Waiting for new files...")

        except Exception as e:
            self.logger.error(f"Error starting file watcher: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop watching for file changes."""
        if self.observer:
            self.logger.info("Stopping file watcher...")
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")
