"""Main audio file processor."""

from pathlib import Path
from typing import Optional
from .config import Config
from .logger import get_logger
from .file_handler import FileHandler
from .tag_handler import TagHandler
from .bpm_detector import BPMDetector


class AudioProcessor:
    """Main processor for audio files."""

    VERSION = "v2.0.0"

    def __init__(self, config: Config):
        """
        Initialize audio processor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.file_handler = FileHandler()
        self.tag_handler = TagHandler()
        self.bpm_detector = BPMDetector()

        # Load copied files list
        self.copied_files = self.file_handler.load_copied_list(config.base_path)

    def process_all(self) -> None:
        """Process all audio files in base directory."""
        self.logger.info("")
        self.logger.info("=" * 63)
        self.logger.info("Starting audio file processing...")
        self.logger.info("=" * 63)

        # Ensure directories exist
        self._ensure_directories()

        # Clean up directories first
        self.file_handler.remove_empty_directories(self.config.base_path)

        # Get all audio files
        audio_files = self.file_handler.get_audio_files(
            self.config.base_path,
            self.config.supported_extensions
        )

        self.logger.info(f"Found {len(audio_files)} audio file(s) to process")

        # Process each file
        for file_path in audio_files:
            if str(file_path) not in self.copied_files:
                self.process_file(file_path)

    def process_file(self, file_path: Path) -> None:
        """
        Process a single audio file.

        Args:
            file_path: Path to audio file
        """
        self.logger.info("")
        self.logger.info("-" * 63)
        self.logger.info(f"PROCESSING: {file_path.name}")

        try:
            # Get current tags
            artist, title, bpm = self.tag_handler.get_tags(file_path)

            if artist and title:
                self.logger.info(f"ID3 Artist: [{artist}]")
                self.logger.info(f"ID3 Title: [{title}]")
                self.logger.info("Tag data OK")
            else:
                self.logger.info("Tag data missing...")

            # Handle BPM detection for MP3 files
            if file_path.suffix.lower() == '.mp3':
                bpm = self._process_bpm(file_path, bpm)

            # Extract artist/title from filename if missing
            if not artist or not title:
                filename_artist, filename_title = self.tag_handler.extract_from_filename(file_path.name)

                if not artist and filename_artist:
                    artist = filename_artist
                    self.tag_handler.set_tags(file_path, artist=artist)
                    self.logger.info(f"Set artist from filename: '{artist}'")

                if not title and filename_title:
                    title = filename_title
                    self.tag_handler.set_tags(file_path, title=title)
                    self.logger.info(f"Set title from filename: '{title}'")

                # Clear extra tags
                self.tag_handler.clear_extra_tags(file_path)

            # Determine output filename
            output_filename = self._get_output_filename(file_path, artist, title)

            # Copy file to destinations
            self._copy_to_destinations(file_path, output_filename)

            # Add to copied list
            self.file_handler.update_copied_list(self.config.base_path, file_path)

            self.logger.info(f"Successfully processed: {file_path.name}")

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")

    def _process_bpm(self, file_path: Path, current_bpm: Optional[int]) -> Optional[int]:
        """
        Process BPM detection and tagging.

        Args:
            file_path: Path to audio file
            current_bpm: Current BPM from tags (if any)

        Returns:
            Final BPM value
        """
        min_bpm, max_bpm = self.config.bpm_range

        # Check if existing BPM is valid
        if current_bpm and self.bpm_detector.is_bpm_valid(current_bpm, min_bpm, max_bpm):
            self.logger.info(f"ID3 BPM: {current_bpm}")
            self.logger.info("Tag BPM OK")
            return current_bpm

        if current_bpm:
            self.logger.warning(f"Tag BPM out of range: {current_bpm}")

        # Detect BPM
        self.logger.info("Tag BPM missing or invalid, detecting...")
        detected_bpm = self.bpm_detector.detect_bpm(file_path)

        if detected_bpm:
            # Try to correct if out of range
            corrected_bpm = self.bpm_detector.get_corrected_bpm(detected_bpm, min_bpm, max_bpm)

            self.logger.info(f"BPM Detected: {corrected_bpm}")

            if self.bpm_detector.is_bpm_valid(corrected_bpm, min_bpm, max_bpm):
                # Save BPM to tags
                self.tag_handler.set_tags(file_path, bpm=corrected_bpm)
                self.logger.info(f"Setting new BPM: [{corrected_bpm}]")
                return corrected_bpm
            else:
                self.logger.warning(f"Detected BPM out of range: {corrected_bpm}")

        return None

    def _get_output_filename(self, file_path: Path, artist: Optional[str], title: Optional[str]) -> str:
        """
        Determine output filename based on tags or cleaned original name.

        Args:
            file_path: Original file path
            artist: Artist name
            title: Track title

        Returns:
            Output filename
        """
        extension = file_path.suffix.lower()

        # Use tag data if available and artist doesn't contain '.'
        if artist and title and len(artist) > 2 and len(title) > 2:
            if '.' not in artist:
                tag_filename = f"{artist} - {title}"
                cleaned = self.file_handler.clean_filename(tag_filename, extension)
                self.logger.info(f"New filename: {cleaned}")
                return cleaned
            else:
                self.logger.info("Using original filename as Artist tag contains '.'")

        # Fall back to cleaned original filename
        cleaned = self.file_handler.clean_filename(file_path.name, extension)
        return cleaned

    def _copy_to_destinations(self, source_path: Path, output_filename: str) -> None:
        """
        Copy file to local and optionally network destinations.

        Args:
            source_path: Source file path
            output_filename: Output filename to use
        """
        # Copy to local path
        local_dest = self.config.local_path / output_filename
        if self.file_handler.copy_file(source_path, local_dest, safe=True):
            # Delete original after successful copy
            self.file_handler.delete_file(source_path)

            # Copy to network share if enabled
            if self.config.include_share and self.config.network_path:
                network_dest = self.config.network_path / output_filename
                self.file_handler.copy_to_network(local_dest, self.config.network_path)

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.config.base_path,
            self.config.local_path,
        ]

        if self.config.desktop_path:
            directories.append(self.config.desktop_path)

        if self.config.include_share and self.config.network_path:
            directories.append(self.config.network_path)

        for directory in directories:
            if directory and not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Creating... {directory}")
