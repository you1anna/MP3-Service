"""CLI commands for MP3 Service."""

import json
from pathlib import Path
from typing import Dict, Any
from .config import Config, create_default_config
from .logger import setup_logger
from .processor import AudioProcessor


class CLI:
    """Command-line interface handler."""

    def __init__(self):
        """Initialize CLI."""
        pass

    def init_config(self, output_path: str, force: bool = False) -> None:
        """
        Create a default configuration file.

        Args:
            output_path: Path to output configuration file
            force: If True, overwrite existing file
        """
        output = Path(output_path)

        if output.exists() and not force:
            print(f"Error: Configuration file already exists: {output_path}")
            print("Use --force to overwrite")
            return

        config = create_default_config()

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Created configuration file: {output_path}")
        print("\nNext steps:")
        print(f"1. Edit {output_path} to customize paths")
        print(f"2. Run: python main.py validate --config {output_path}")
        print(f"3. Run: python main.py test --config {output_path}")
        print(f"4. Run: python main.py start --config {output_path}")

    def validate_config(self, config_path: str) -> None:
        """
        Validate configuration file.

        Args:
            config_path: Path to configuration file
        """
        print(f"Validating configuration: {config_path}")
        print("")

        try:
            config = Config(config_path)
            print("✓ Configuration file loaded successfully")
            print("")

            # Check paths
            issues = []
            warnings = []

            if not config.base_path.exists():
                issues.append(f"Base path does not exist: {config.base_path}")
            else:
                print(f"✓ Base path exists: {config.base_path}")

            if not config.local_path.exists():
                warnings.append(f"Local path does not exist (will be created): {config.local_path}")
            else:
                print(f"✓ Local path exists: {config.local_path}")

            if config.include_share:
                if not config.network_path:
                    issues.append("Network share enabled but network_path not set")
                elif not config.network_path.exists():
                    warnings.append(f"Network path does not exist: {config.network_path}")
                else:
                    print(f"✓ Network path exists: {config.network_path}")

            if config.poll_interval < 5:
                warnings.append(f"Poll interval is very low ({config.poll_interval}s), may cause high CPU usage")

            print("")

            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"  ⚠ {warning}")
                print("")

            if issues:
                print("Issues:")
                for issue in issues:
                    print(f"  ✗ {issue}")
                print("")
                print("Please fix these issues before starting the service.")
            else:
                print("✓ Configuration is valid!")
                print("")
                print("Run 'python main.py test' to preview what will be processed.")

        except FileNotFoundError:
            print(f"✗ Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in configuration file: {e}")
        except ValueError as e:
            print(f"✗ Configuration error: {e}")
        except Exception as e:
            print(f"✗ Error validating configuration: {e}")

    def test_config(self, config_path: str) -> None:
        """
        Test configuration and show what would be processed.

        Args:
            config_path: Path to configuration file
        """
        print("Testing configuration and scanning for files...")
        print("")

        try:
            config = Config(config_path)
            logger = setup_logger("MP3Service.Test", level="INFO")
            processor = AudioProcessor(config, dry_run=True)

            print(f"Base Path: {config.base_path}")
            print(f"Local Path: {config.local_path}")
            print(f"Supported Extensions: {', '.join(config.supported_extensions)}")
            print(f"BPM Range: {config.bpm_range[0]}-{config.bpm_range[1]}")
            print("")

            # Get files
            audio_files = processor.file_handler.get_audio_files(
                config.base_path,
                config.supported_extensions
            )

            if not audio_files:
                print("No audio files found to process.")
                return

            print(f"Found {len(audio_files)} audio file(s):")
            print("")

            # Show first 10 files
            for i, file_path in enumerate(audio_files[:10], 1):
                print(f"  {i}. {file_path.name}")
                print(f"     Location: {file_path.parent}")

                # Get tags
                artist, title, bpm = processor.tag_handler.get_tags(file_path)
                if artist or title:
                    print(f"     Tags: {artist or '(none)'} - {title or '(none)'} [{bpm or 'no BPM'}]")

                # Show what output would be
                output_filename = processor._get_output_filename(file_path, artist, title)
                print(f"     Output: {output_filename}")
                print("")

            if len(audio_files) > 10:
                print(f"  ... and {len(audio_files) - 10} more files")
                print("")

            print("Run 'python main.py start --dry-run' to see full processing without making changes.")
            print("Run 'python main.py start' to actually process the files.")

        except Exception as e:
            print(f"Error testing configuration: {e}")

    def show_status(self, config_path: str) -> None:
        """
        Show service status and configuration.

        Args:
            config_path: Path to configuration file
        """
        print("MP3 Service Status")
        print("=" * 70)
        print("")

        try:
            config = Config(config_path)

            print(f"Configuration File: {config_path}")
            print(f"Log File: {config.log_file}")
            print(f"Log Level: {config.log_level}")
            print("")

            print("Paths:")
            print(f"  Base Path: {config.base_path}")
            print(f"    Status: {'✓ Exists' if config.base_path.exists() else '✗ Does not exist'}")
            print(f"  Local Path: {config.local_path}")
            print(f"    Status: {'✓ Exists' if config.local_path.exists() else '✗ Does not exist'}")

            if config.include_share and config.network_path:
                print(f"  Network Path: {config.network_path}")
                print(f"    Status: {'✓ Exists' if config.network_path.exists() else '✗ Does not exist'}")

            print("")

            print("Settings:")
            print(f"  Poll Interval: {config.poll_interval} seconds")
            print(f"  Network Share: {'Enabled' if config.include_share else 'Disabled'}")
            print(f"  BPM Range: {config.bpm_range[0]}-{config.bpm_range[1]}")
            print(f"  Supported Formats: {', '.join(config.supported_extensions)}")
            print("")

            # Count files
            processor = AudioProcessor(config, dry_run=True)
            audio_files = processor.file_handler.get_audio_files(
                config.base_path,
                config.supported_extensions
            )

            print(f"Files to Process: {len(audio_files)}")

            # Check log file
            if config.log_file.exists():
                log_size = config.log_file.stat().st_size
                print(f"Log File Size: {log_size:,} bytes")

        except Exception as e:
            print(f"Error getting status: {e}")
