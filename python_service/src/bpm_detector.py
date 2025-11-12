"""BPM detection for audio files using librosa."""

from pathlib import Path
from typing import Optional
import warnings

# Suppress librosa warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from .logger import get_logger


class BPMDetector:
    """Detects BPM (tempo) of audio files."""

    def __init__(self):
        """Initialize BPM detector."""
        self.logger = get_logger(__name__)

        if not LIBROSA_AVAILABLE:
            self.logger.warning(
                "librosa not available. BPM detection will be disabled. "
                "Install with: pip install librosa"
            )

    def detect_bpm(self, file_path: Path) -> Optional[int]:
        """
        Detect BPM of an audio file.

        Args:
            file_path: Path to audio file

        Returns:
            BPM as integer, or None if detection fails
        """
        if not LIBROSA_AVAILABLE:
            self.logger.warning("librosa not installed, cannot detect BPM")
            return None

        try:
            # Load audio file
            self.logger.debug(f"Loading audio for BPM detection: {file_path.name}")
            y, sr = librosa.load(str(file_path), sr=None, duration=120)  # Analyze first 2 minutes

            # Detect tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

            # Convert to integer
            bpm = int(round(tempo))

            self.logger.debug(f"Detected BPM: {bpm} for {file_path.name}")
            return bpm

        except Exception as e:
            self.logger.error(f"Error detecting BPM for {file_path}: {e}")
            return None

    def is_bpm_valid(self, bpm: Optional[int], min_bpm: int, max_bpm: int) -> bool:
        """
        Check if BPM is within valid range.

        Args:
            bpm: BPM value to check
            min_bpm: Minimum acceptable BPM
            max_bpm: Maximum acceptable BPM

        Returns:
            True if BPM is valid, False otherwise
        """
        if bpm is None:
            return False

        return min_bpm <= bpm <= max_bpm

    def get_corrected_bpm(self, bpm: int, min_bpm: int, max_bpm: int) -> int:
        """
        Correct BPM if it's double-time or half-time.

        Sometimes librosa detects at double or half the actual tempo.
        This attempts to correct it to fit within the expected range.

        Args:
            bpm: Detected BPM
            min_bpm: Minimum acceptable BPM
            max_bpm: Maximum acceptable BPM

        Returns:
            Corrected BPM
        """
        if self.is_bpm_valid(bpm, min_bpm, max_bpm):
            return bpm

        # Try half-time
        half_bpm = bpm // 2
        if self.is_bpm_valid(half_bpm, min_bpm, max_bpm):
            self.logger.debug(f"Corrected BPM from {bpm} to {half_bpm} (half-time)")
            return half_bpm

        # Try double-time
        double_bpm = bpm * 2
        if self.is_bpm_valid(double_bpm, min_bpm, max_bpm):
            self.logger.debug(f"Corrected BPM from {bpm} to {double_bpm} (double-time)")
            return double_bpm

        # No valid correction found, return original
        return bpm
