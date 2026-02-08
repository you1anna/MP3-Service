"""ID3 tag handling for audio files."""

from pathlib import Path
from typing import Optional, Tuple
import mutagen
from mutagen.id3 import ID3, TPE1, TIT2, TBPM
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from .logger import get_logger


class TagHandler:
    """Handles reading and writing ID3 tags for audio files."""

    def __init__(self):
        """Initialize TagHandler."""
        self.logger = get_logger(__name__)

    def get_tags(self, file_path: Path) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Extract artist, title, and BPM from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (artist, title, bpm) - any can be None if not found
        """
        artist = None
        title = None
        bpm = None

        try:
            audio = mutagen.File(file_path)

            if audio is None:
                self.logger.warning(f"Could not load audio file: {file_path}")
                return (None, None, None)

            # Handle different file formats
            if isinstance(audio, MP4):
                # M4A files
                artist = self._get_mp4_tag(audio, '\xa9ART')
                title = self._get_mp4_tag(audio, '\xa9nam')
                bpm_data = self._get_mp4_tag(audio, 'tmpo')
                if bpm_data:
                    try:
                        bpm = int(bpm_data[0]) if isinstance(bpm_data, list) else int(bpm_data)
                    except (ValueError, TypeError):
                        pass

            elif isinstance(audio, FLAC):
                # FLAC files
                artist = self._get_flac_tag(audio, 'artist')
                title = self._get_flac_tag(audio, 'title')
                bpm_data = self._get_flac_tag(audio, 'bpm')
                if bpm_data:
                    try:
                        bpm = int(float(bpm_data))
                    except (ValueError, TypeError):
                        pass

            else:
                # MP3 and other ID3 formats
                if hasattr(audio, 'tags') and audio.tags:
                    artist = self._get_id3_tag(audio, 'TPE1')
                    title = self._get_id3_tag(audio, 'TIT2')
                    bpm_data = self._get_id3_tag(audio, 'TBPM')
                    if bpm_data:
                        try:
                            bpm = int(float(str(bpm_data)))
                        except (ValueError, TypeError):
                            pass

            self.logger.debug(f"Tags for {file_path.name}: Artist={artist}, Title={title}, BPM={bpm}")

        except Exception as e:
            self.logger.error(f"Error reading tags from {file_path}: {e}")

        return (artist, title, bpm)

    def set_tags(
        self,
        file_path: Path,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        bpm: Optional[int] = None
    ) -> bool:
        """
        Write artist, title, and/or BPM to audio file.

        Args:
            file_path: Path to audio file
            artist: Artist name (optional)
            title: Track title (optional)
            bpm: Beats per minute (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            audio = mutagen.File(file_path)

            if audio is None:
                self.logger.error(f"Could not load audio file: {file_path}")
                return False

            # Handle different file formats
            if isinstance(audio, MP4):
                # M4A files
                if artist:
                    audio['\xa9ART'] = artist
                if title:
                    audio['\xa9nam'] = title
                if bpm:
                    audio['tmpo'] = [bpm]

            elif isinstance(audio, FLAC):
                # FLAC files
                if artist:
                    audio['artist'] = artist
                if title:
                    audio['title'] = title
                if bpm:
                    audio['bpm'] = str(bpm)

            else:
                # MP3 and other ID3 formats
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.add_tags()

                if artist:
                    audio.tags['TPE1'] = TPE1(encoding=3, text=artist)
                if title:
                    audio.tags['TIT2'] = TIT2(encoding=3, text=title)
                if bpm:
                    audio.tags['TBPM'] = TBPM(encoding=3, text=str(bpm))

            audio.save()
            self.logger.debug(f"Saved tags for {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Error writing tags to {file_path}: {e}")
            return False

    def extract_from_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract artist and title from filename (format: Artist - Title.ext).

        Args:
            filename: Filename to parse

        Returns:
            Tuple of (artist, title) - either can be None
        """
        # Remove extension
        name = Path(filename).stem

        # Split on first dash
        if ' - ' in name:
            parts = name.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            return (artist, title)
        elif '-' in name:
            parts = name.split('-', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            return (artist, title)

        return (None, None)

    def _get_id3_tag(self, audio, tag_name: str) -> Optional[str]:
        """Helper to get ID3 tag value."""
        try:
            if tag_name in audio.tags:
                return str(audio.tags[tag_name].text[0])
        except (AttributeError, IndexError, KeyError):
            pass
        return None

    def _get_mp4_tag(self, audio: MP4, tag_name: str) -> Optional[str]:
        """Helper to get MP4 tag value."""
        try:
            if tag_name in audio:
                value = audio[tag_name]
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
        except (AttributeError, IndexError, KeyError):
            pass
        return None

    def _get_flac_tag(self, audio: FLAC, tag_name: str) -> Optional[str]:
        """Helper to get FLAC tag value."""
        try:
            if tag_name in audio:
                value = audio[tag_name]
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
        except (AttributeError, IndexError, KeyError):
            pass
        return None

    def clear_extra_tags(self, file_path: Path) -> bool:
        """
        Clear unnecessary tags (album artists, composers, comments, grouping).

        Args:
            file_path: Path to audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            audio = mutagen.File(file_path)

            if audio is None:
                return False

            if isinstance(audio, MP4):
                # Clear M4A tags
                tags_to_clear = ['\xa9alb', '\xa9wrt', '\xa9cmt', '\xa9grp', 'aART']
                for tag in tags_to_clear:
                    if tag in audio:
                        del audio[tag]

            elif isinstance(audio, FLAC):
                # Clear FLAC tags
                tags_to_clear = ['albumartist', 'composer', 'comment', 'grouping']
                for tag in tags_to_clear:
                    if tag in audio:
                        del audio[tag]

            else:
                # Clear ID3 tags
                if hasattr(audio, 'tags') and audio.tags:
                    tags_to_clear = ['TPE2', 'TCOM', 'COMM', 'TIT1']
                    for tag in tags_to_clear:
                        if tag in audio.tags:
                            del audio.tags[tag]

            audio.save()
            return True

        except Exception as e:
            self.logger.error(f"Error clearing extra tags from {file_path}: {e}")
            return False
