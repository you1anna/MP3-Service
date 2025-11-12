"""File handling operations including cleaning and copying."""

import re
import shutil
from pathlib import Path
from typing import List, Optional
from .logger import get_logger


class FileHandler:
    """Handles file operations and filename cleaning."""

    # Regex patterns for filename cleaning (from original C# code)
    PATTERNS = [
        (r'--', ' - '),  # Replace double dashes with single dash
        (r'[_]{1,}', ' '),  # Replace underscores with spaces
        (r'^[a-cA-C0-9]{1,3}[\s-_\.]+', ''),  # Remove leading numbers/letters
        (r'(\()*(_-\s)*(www\.*)*-*[a-zA-Z0-9\(\-]+\.[\[\(]*(net|com|org|ru)+[\)\]*[\d]*', ''),  # Remove website patterns
        (r'(?!\)-)[-_\)]+[a-zA-Z0-9]{2,3}\.', '.'),  # Clean up before extension
        (r'[-_]*siberia', ''),  # Remove 'siberia' pattern
    ]

    def __init__(self):
        """Initialize FileHandler."""
        self.logger = get_logger(__name__)
        self.copied_files: set = set()
        self.copied_list_file = "copiedList.txt"

    def clean_filename(self, filename: str, extension: str) -> str:
        """
        Clean filename using regex patterns.

        Args:
            filename: Original filename
            extension: File extension (e.g., '.mp3')

        Returns:
            Cleaned filename with extension
        """
        # Remove extension for processing
        name = filename.replace(extension, '')

        # Apply all regex patterns
        for pattern, replacement in self.PATTERNS:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        # Convert to title case
        name = name.strip().title()

        # Add extension back
        return f"{name}{extension}"

    def get_audio_files(self, directory: Path, extensions: tuple) -> List[Path]:
        """
        Get all audio files from directory and subdirectories.

        Args:
            directory: Directory to search
            extensions: Tuple of file extensions to include

        Returns:
            List of audio file paths
        """
        audio_files = []

        try:
            for ext in extensions:
                # Handle both lowercase and uppercase extensions
                audio_files.extend(directory.rglob(f"*{ext}"))
                audio_files.extend(directory.rglob(f"*{ext.upper()}"))

            # Filter out INCOMPLETE files
            audio_files = [
                f for f in audio_files
                if "INCOMPLETE~" not in f.name
            ]

            return audio_files

        except Exception as e:
            self.logger.error(f"Error getting audio files: {e}")
            return []

    def load_copied_list(self, base_path: Path) -> set:
        """
        Load list of previously copied files.

        Args:
            base_path: Base directory path

        Returns:
            Set of file paths that have been copied
        """
        list_file = base_path / self.copied_list_file

        if not list_file.exists():
            # Create the file if it doesn't exist
            list_file.touch()
            return set()

        try:
            with open(list_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            self.logger.error(f"Error loading copied list: {e}")
            return set()

    def update_copied_list(self, base_path: Path, file_path: Path) -> None:
        """
        Add file to copied list.

        Args:
            base_path: Base directory path
            file_path: File path to add to list
        """
        list_file = base_path / self.copied_list_file

        try:
            with open(list_file, 'a', encoding='utf-8') as f:
                f.write(f"{file_path}\n")
            self.copied_files.add(str(file_path))
        except Exception as e:
            self.logger.error(f"Error updating copied list: {e}")

    def copy_file(self, source: Path, destination: Path, safe: bool = True) -> bool:
        """
        Copy file to destination with optional safety check.

        Args:
            source: Source file path
            destination: Destination file path
            safe: If True, don't overwrite existing files

        Returns:
            True if copy successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            if safe and destination.exists():
                # Add _1 to filename if exists
                stem = destination.stem
                suffix = destination.suffix
                destination = destination.parent / f"{stem}_1{suffix}"
                self.logger.warning(f"File exists, copying as: {destination.name}")

            shutil.copy2(source, destination)
            self.logger.info(f"Copied: {source.name} -> {destination}")
            return True

        except Exception as e:
            self.logger.error(f"Error copying file {source} to {destination}: {e}")
            return False

    def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            file_path.unlink()
            self.logger.info(f"Deleted: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting file {file_path}: {e}")
            return False

    def remove_empty_directories(self, directory: Path) -> None:
        """
        Remove empty subdirectories and clean up non-audio files.

        Args:
            directory: Directory to clean
        """
        try:
            for subdir in directory.iterdir():
                if not subdir.is_dir():
                    continue

                # Remove non-audio files (excluding txt files)
                for file in subdir.iterdir():
                    if file.is_file():
                        # Keep audio files and txt files
                        if not (file.suffix.lower() in ['.mp3', '.m4a', '.wav', '.aif', '.aiff', '.flac', '.txt']):
                            if not file.name.startswith("INCOMPLETE~"):
                                try:
                                    file.unlink()
                                    self.logger.info(f"Removed non-audio file: {file}")
                                except Exception as e:
                                    self.logger.error(f"Error removing file {file}: {e}")

                # Remove directory if empty
                try:
                    if not any(subdir.iterdir()):
                        subdir.rmdir()
                        self.logger.info(f"Removed empty directory: {subdir}")
                except Exception as e:
                    self.logger.debug(f"Directory not empty or error: {e}")

        except Exception as e:
            self.logger.error(f"Error removing directories: {e}")

    def copy_to_network(self, source: Path, network_path: Path) -> bool:
        """
        Copy file to network share.

        Args:
            source: Source file path
            network_path: Network destination path

        Returns:
            True if copy successful, False otherwise
        """
        if not network_path.exists():
            self.logger.error(f"Network path does not exist: {network_path}")
            return False

        destination = network_path / source.name

        if destination.exists():
            self.logger.debug(f"File already exists on network: {source.name}")
            return True

        try:
            shutil.copy2(source, destination)
            self.logger.info(f"Published to network: {source.name}")
            return True
        except Exception as e:
            self.logger.error(f"Network copy error: {e}")
            return False
