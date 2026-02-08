#!/usr/bin/env python3
"""
MP3 Service - Audio File Processor
Main entry point with CLI interface.
"""

import argparse
import sys
import time
import signal
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config, create_default_config
from src.logger import setup_logger
from src.processor import AudioProcessor
from src.cli import CLI


class MP3Service:
    """Main service class for audio processing."""

    def __init__(self, config_path: str = "config.json", dry_run: bool = False, watch: bool = False):
        """
        Initialize the MP3 service.

        Args:
            config_path: Path to configuration file
            dry_run: If True, preview changes without modifying files
            watch: If True, use file watching instead of polling
        """
        self.config = Config(config_path)
        self.dry_run = dry_run
        self.watch = watch
        self.logger = setup_logger(
            "MP3Service",
            log_file=self.config.log_file,
            level=self.config.log_level
        )
        self.processor = AudioProcessor(self.config, dry_run=dry_run)
        self.running = False
        self.watcher = None

    def start(self) -> None:
        """Start the service."""
        mode = "DRY-RUN MODE" if self.dry_run else "LIVE MODE"
        watch_mode = "File Watching" if self.watch else "Polling"

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info(f" MP3 Service {AudioProcessor.VERSION} - {mode}")
        self.logger.info("=" * 70)
        self.logger.info(f"Mode: {watch_mode}")
        self.logger.info(f"Base Path: {self.config.base_path}")
        self.logger.info(f"Local Path: {self.config.local_path}")

        if not self.watch:
            self.logger.info(f"Poll Interval: {self.config.poll_interval} seconds")

        self.logger.info(f"Network Share: {'Enabled' if self.config.include_share else 'Disabled'}")
        if self.config.include_share and self.config.network_path:
            self.logger.info(f"Network Path: {self.config.network_path}")

        if self.dry_run:
            self.logger.warning("DRY-RUN: No files will be modified or moved")

        self.logger.info("")

        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if self.watch:
            self._start_watching()
        else:
            self._start_polling()

    def _start_polling(self) -> None:
        """Start polling mode."""
        # Run initial processing
        try:
            stats = self.processor.process_all()
            self._print_stats(stats)
        except Exception as e:
            self.logger.error(f"Error during initial processing: {e}", exc_info=True)

        # Main polling loop
        while self.running:
            try:
                time.sleep(self.config.poll_interval)
                self.logger.info("")
                self.logger.info("Polling for new files...")
                stats = self.processor.process_all()
                self._print_stats(stats)
            except Exception as e:
                self.logger.error(f"Error during polling cycle: {e}", exc_info=True)

    def _start_watching(self) -> None:
        """Start file watching mode."""
        try:
            from src.watcher import FileWatcher

            self.watcher = FileWatcher(self.config, self.processor)
            self.logger.info("Starting file watcher...")

            # Run initial processing
            stats = self.processor.process_all()
            self._print_stats(stats)

            # Start watching
            self.watcher.start()

            # Keep main thread alive
            while self.running:
                time.sleep(1)

        except ImportError:
            self.logger.error("watchdog library not installed. Install with: pip install watchdog")
            self.logger.info("Falling back to polling mode...")
            self._start_polling()
        except Exception as e:
            self.logger.error(f"Error in file watching: {e}", exc_info=True)

    def _print_stats(self, stats: dict) -> None:
        """Print processing statistics."""
        if stats.get('processed', 0) > 0:
            self.logger.info("")
            self.logger.info(f"Statistics: Processed={stats.get('processed', 0)}, "
                           f"Errors={stats.get('errors', 0)}, "
                           f"Skipped={stats.get('skipped', 0)}")

    def stop(self) -> None:
        """Stop the service."""
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("MP3 Service stopping...")
        self.logger.info("=" * 70)

        if self.watcher:
            self.watcher.stop()

        self.running = False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description="MP3 Service - Automated audio file processor with BPM detection and tag management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    Start service with default config
  %(prog)s start --dry-run          Preview changes without modifying files
  %(prog)s start --watch            Use file watching instead of polling
  %(prog)s test                     Test configuration and preview files
  %(prog)s validate                 Validate configuration file
  %(prog)s init                     Create default configuration file
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {AudioProcessor.VERSION}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start the audio processing service')
    start_parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    start_parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Preview changes without modifying files'
    )
    start_parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Use file watching instead of polling (requires watchdog)'
    )

    # Test command
    test_parser = subparsers.add_parser('test', help='Test configuration and preview files')
    test_parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file'
    )

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration file')
    validate_parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file'
    )

    # Init command
    init_parser = subparsers.add_parser('init', help='Create default configuration file')
    init_parser.add_argument(
        '--output', '-o',
        default='config.json',
        help='Output path for configuration file'
    )
    init_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing file'
    )

    # Process command (one-time processing)
    process_parser = subparsers.add_parser('process', help='Process files once and exit')
    process_parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file'
    )
    process_parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Preview changes without modifying files'
    )

    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status and configuration')
    status_parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    cli = CLI()

    try:
        if args.command == 'init':
            cli.init_config(args.output, args.force)

        elif args.command == 'validate':
            cli.validate_config(args.config)

        elif args.command == 'test':
            cli.test_config(args.config)

        elif args.command == 'status':
            cli.show_status(args.config)

        elif args.command == 'process':
            service = MP3Service(args.config, dry_run=args.dry_run, watch=False)
            stats = service.processor.process_all()
            service._print_stats(stats)
            print("\nProcessing complete!")

        elif args.command == 'start':
            service = MP3Service(args.config, dry_run=args.dry_run, watch=args.watch)
            service.start()

    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
