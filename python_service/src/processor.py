"""Main audio file processor."""

import subprocess
from pathlib import Path
from typing import Optional, Dict
from .config import Config
from .logger import get_logger
from .file_handler import FileHandler
from .tag_handler import TagHandler
from .bpm_detector import BPMDetector
from .rekordbox_xml import RekordboxXMLWriter
from .ssd_archive import SSDArchiver


class AudioProcessor:
    """Main processor for audio files."""

    VERSION = "v2.0.0"

    def __init__(self, config: Config, dry_run: bool = False):
        """
        Initialize audio processor.

        Args:
            config: Configuration object
            dry_run: If True, preview changes without modifying files
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = get_logger(__name__)
        self.file_handler = FileHandler()
        self.tag_handler = TagHandler()
        self.bpm_detector = BPMDetector()
        self.rekordbox_xml = RekordboxXMLWriter(config.rekordbox_xml_path)
        self.ssd_archiver = SSDArchiver(config.ssd_archive_path)

        # Statistics
        self.stats = {
            'processed': 0,
            'errors': 0,
            'skipped': 0
        }

        # Load copied files list
        self.copied_files = self.file_handler.load_copied_list(config.base_path)

    def process_all(self) -> Dict[str, int]:
        """
        Process all audio files in base directory.

        Returns:
            Statistics dictionary with counts
        """
        # Reset statistics
        self.stats = {'processed': 0, 'errors': 0, 'skipped': 0}

        self.logger.info("")
        self.logger.info("=" * 63)
        self.logger.info("Starting audio file processing...")
        self.logger.info("=" * 63)

        # Ensure directories exist
        if not self.dry_run:
            self._ensure_directories()

        # Clean up directories first
        if not self.dry_run:
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
            else:
                self.stats['skipped'] += 1

        return self.stats

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

            is_flac = file_path.suffix.lower() == '.flac'

            # Handle BPM detection for all audio files (skip in dry-run for speed)
            if not self.dry_run:
                bpm = self._process_bpm(file_path, bpm)

            if is_flac:
                # FLAC: convert to AIFF, keep original
                self._process_flac(file_path, artist, title, bpm)
            else:
                # Non-FLAC: clean metadata/filename, move to Processed
                self._process_standard(file_path, artist, title, bpm)

            # Add to copied list
            if not self.dry_run:
                self.file_handler.update_copied_list(self.config.base_path, file_path)

            self.logger.info(f"{'Would process' if self.dry_run else 'Successfully processed'}: {file_path.name}")
            self.stats['processed'] += 1

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            self.stats['errors'] += 1

    def _process_standard(self, file_path: Path, artist: Optional[str], title: Optional[str], bpm: Optional[int] = None) -> None:
        """Process a non-FLAC audio file: clean tags/filename, move to Processed."""
        # Extract artist/title from filename if missing
        if not artist or not title:
            filename_artist, filename_title = self.tag_handler.extract_from_filename(file_path.name)

            if not artist and filename_artist:
                artist = filename_artist
                if not self.dry_run:
                    self.tag_handler.set_tags(file_path, artist=artist)
                self.logger.info(f"{'Would set' if self.dry_run else 'Set'} artist from filename: '{artist}'")

            if not title and filename_title:
                title = filename_title
                if not self.dry_run:
                    self.tag_handler.set_tags(file_path, title=title)
                self.logger.info(f"{'Would set' if self.dry_run else 'Set'} title from filename: '{title}'")

            # Clear extra tags
            if not self.dry_run:
                self.tag_handler.clear_extra_tags(file_path)

        # Determine output filename
        output_filename = self._get_output_filename(file_path, artist, title)

        # Copy file to destinations (and delete original)
        local_dest = self._copy_to_destinations(file_path, output_filename, delete_original=True)

        if local_dest is not None:
            # Move to SSD if configured and mounted; otherwise stay local
            final_dest = self.ssd_archiver.relocate(local_dest)
            # Register in Rekordbox XML library (no-op if not configured / fails safely)
            self.rekordbox_xml.register(final_dest, artist, title, bpm)

    def _process_flac(self, file_path: Path, artist: Optional[str], title: Optional[str], bpm: Optional[int]) -> None:
        """Process a FLAC file: convert to AIFF, copy tags, move AIFF to Processed, keep original."""
        # Extract artist/title from filename if missing from tags
        if not artist or not title:
            filename_artist, filename_title = self.tag_handler.extract_from_filename(file_path.name)
            if not artist and filename_artist:
                artist = filename_artist
            if not title and filename_title:
                title = filename_title

        # Determine output filename with .aiff extension
        output_filename = self._get_output_filename(file_path, artist, title, override_ext='.aiff')

        if self.dry_run:
            self.logger.info(f"Would convert FLAC to AIFF: {file_path.name} -> {output_filename}")
            return

        # Convert FLAC to AIFF via ffmpeg
        aiff_dest = self.config.local_path / output_filename
        aiff_dest.parent.mkdir(parents=True, exist_ok=True)

        if not self._convert_flac_to_aiff(file_path, aiff_dest):
            self.stats['errors'] += 1
            self.stats['processed'] -= 1  # will be incremented by caller
            return

        # Copy tags (artist, title, BPM) to the new AIFF
        self.tag_handler.set_tags(aiff_dest, artist=artist, title=title, bpm=bpm)
        self.tag_handler.clear_extra_tags(aiff_dest)

        self.logger.info(f"Converted FLAC->AIFF: {file_path.name} -> {output_filename}")
        self.logger.info(f"Original FLAC kept: {file_path}")

        # Also copy to network share if enabled
        if self.config.include_share and self.config.network_path:
            self.file_handler.copy_to_network(aiff_dest, self.config.network_path)

        # Move to SSD if configured and mounted; otherwise stay local
        final_dest = self.ssd_archiver.relocate(aiff_dest)
        # Register in Rekordbox XML library (no-op if not configured / fails safely)
        self.rekordbox_xml.register(final_dest, artist, title, bpm)

    def _convert_flac_to_aiff(self, input_path: Path, output_path: Path) -> bool:
        """Convert FLAC to 16-bit/44.1kHz AIFF using ffmpeg."""
        try:
            input_abs = input_path.resolve(strict=True)
            output_abs = output_path.resolve()
            if not str(input_abs).startswith('/') or not str(output_abs).startswith('/'):
                self.logger.error(f"Refusing non-absolute ffmpeg path: {input_abs} / {output_abs}")
                return False
            cmd = [
                'ffmpeg', '-y', '-i', str(input_abs),
                '-acodec', 'pcm_s16be',
                '-ar', '44100',
                '-f', 'aiff',
                str(output_abs)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                self.logger.error(f"ffmpeg conversion failed: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            self.logger.error(f"ffmpeg conversion timed out for {input_path}")
            return False
        except FileNotFoundError:
            self.logger.error("ffmpeg not found. Install with: brew install ffmpeg")
            return False
        except Exception as e:
            self.logger.error(f"Error converting FLAC to AIFF: {e}")
            return False

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
                return corrected_bpm

        # Detection failed — return tag BPM (even if out of range) for filtering
        return current_bpm

    def _get_output_filename(self, file_path: Path, artist: Optional[str], title: Optional[str], override_ext: Optional[str] = None) -> str:
        """
        Determine output filename based on tags or cleaned original name.

        Args:
            file_path: Original file path
            artist: Artist name
            title: Track title
            override_ext: Override the file extension (e.g. '.aiff' for FLAC conversion)

        Returns:
            Output filename
        """
        extension = override_ext if override_ext else file_path.suffix.lower()

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

    def _copy_to_destinations(self, source_path: Path, output_filename: str, delete_original: bool = True) -> Optional[Path]:
        """
        Copy file to local and optionally network destinations.

        Args:
            source_path: Source file path
            output_filename: Output filename to use
            delete_original: If True, delete the source file after copying

        Returns:
            The final local destination path on success, None on failure or dry-run.
        """
        # Copy to local path
        local_dest = self.config.local_path / output_filename

        if self.dry_run:
            self.logger.info(f"Would copy: {source_path.name} -> {local_dest}")
            if self.config.include_share and self.config.network_path:
                network_dest = self.config.network_path / output_filename
                self.logger.info(f"Would publish to network: {network_dest}")
            return None

        if self.file_handler.copy_file(source_path, local_dest, safe=True):
            # Delete original after successful copy (unless told not to)
            if delete_original:
                backup = self.config.backup_path if self.config.backup_before_delete else None
                self.file_handler.delete_file(source_path, backup_path=backup)

            # Copy to network share if enabled
            if self.config.include_share and self.config.network_path:
                network_dest = self.config.network_path / output_filename
                self.file_handler.copy_to_network(local_dest, self.config.network_path)

            return local_dest

        return None

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
