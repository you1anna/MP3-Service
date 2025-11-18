"""Health check and diagnostics for MP3 Service."""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import platform

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.logger import get_logger


class HealthCheck:
    """System health checker for MP3 Service."""

    def __init__(self, config_path: str = "config.json"):
        """Initialize health checker."""
        self.config_path = config_path
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def run_all_checks(self) -> bool:
        """
        Run all health checks.

        Returns:
            True if all checks pass, False otherwise
        """
        print("=" * 70)
        print("  MP3 Service Health Check")
        print("=" * 70)
        print()

        checks = [
            ("System Information", self.check_system),
            ("Python Environment", self.check_python),
            ("Dependencies", self.check_dependencies),
            ("Configuration", self.check_configuration),
            ("File Paths", self.check_paths),
            ("Permissions", self.check_permissions),
            ("Disk Space", self.check_disk_space),
        ]

        all_passed = True
        for name, check_func in checks:
            print(f"🔍 {name}")
            print("-" * 70)
            passed = check_func()
            if not passed:
                all_passed = False
            print()

        # Summary
        print("=" * 70)
        print("  Summary")
        print("=" * 70)

        if self.issues:
            print("\n❌ Issues Found:")
            for issue in self.issues:
                print(f"  • {issue}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")

        if self.info:
            print("\nℹ️  Information:")
            for info in self.info:
                print(f"  • {info}")

        print()
        if all_passed and not self.issues:
            print("✅ All health checks passed!")
            return True
        else:
            print("❌ Some health checks failed. Review issues above.")
            return False

    def check_system(self) -> bool:
        """Check system information."""
        try:
            print(f"  Platform: {platform.system()} {platform.release()}")
            print(f"  Machine: {platform.machine()}")
            print(f"  Processor: {platform.processor()}")
            return True
        except Exception as e:
            self.issues.append(f"System check failed: {e}")
            return False

    def check_python(self) -> bool:
        """Check Python version."""
        version = sys.version_info
        print(f"  Python: {version.major}.{version.minor}.{version.micro}")
        print(f"  Executable: {sys.executable}")

        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.issues.append(f"Python 3.8+ required, found {version.major}.{version.minor}")
            return False

        print("  ✅ Python version OK")
        return True

    def check_dependencies(self) -> bool:
        """Check required dependencies."""
        required = {
            'mutagen': 'Audio tag manipulation',
        }

        optional = {
            'librosa': 'BPM detection',
            'numpy': 'Numerical operations',
            'watchdog': 'File system watching',
            'soundfile': 'Audio I/O',
        }

        all_ok = True

        for package, description in required.items():
            try:
                __import__(package)
                print(f"  ✅ {package} ({description})")
            except ImportError:
                print(f"  ❌ {package} ({description}) - REQUIRED")
                self.issues.append(f"Missing required package: {package}")
                all_ok = False

        for package, description in optional.items():
            try:
                module = __import__(package)
                version = getattr(module, '__version__', 'unknown')
                print(f"  ✅ {package} v{version} ({description})")
            except ImportError:
                print(f"  ⚠️  {package} ({description}) - optional")
                self.warnings.append(f"Optional package not installed: {package}")

        return all_ok

    def check_configuration(self) -> bool:
        """Check configuration file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            print(f"  ❌ Configuration file not found: {self.config_path}")
            self.issues.append("Configuration file missing")
            return False

        try:
            config = Config(self.config_path)
            print(f"  ✅ Configuration loaded: {self.config_path}")
            print(f"     Base path: {config.base_path}")
            print(f"     Local path: {config.local_path}")
            print(f"     Poll interval: {config.poll_interval}s")
            print(f"     Network share: {'Enabled' if config.include_share else 'Disabled'}")
            return True
        except Exception as e:
            print(f"  ❌ Configuration error: {e}")
            self.issues.append(f"Configuration invalid: {e}")
            return False

    def check_paths(self) -> bool:
        """Check file paths."""
        try:
            config = Config(self.config_path)
            all_ok = True

            paths_to_check = [
                ("Base path", config.base_path, True),
                ("Local path", config.local_path, False),
            ]

            if config.include_share and config.network_path:
                paths_to_check.append(("Network path", config.network_path, False))

            for name, path, required in paths_to_check:
                if path and path.exists():
                    print(f"  ✅ {name}: {path}")
                elif required:
                    print(f"  ❌ {name} does not exist: {path}")
                    self.issues.append(f"{name} missing: {path}")
                    all_ok = False
                else:
                    print(f"  ⚠️  {name} does not exist: {path} (will be created)")
                    self.warnings.append(f"{name} will be created on first run")

            return all_ok
        except Exception as e:
            self.issues.append(f"Path check failed: {e}")
            return False

    def check_permissions(self) -> bool:
        """Check file permissions."""
        try:
            config = Config(self.config_path)
            all_ok = True

            # Check base path readable
            if config.base_path.exists():
                try:
                    list(config.base_path.iterdir())
                    print(f"  ✅ Can read base path")
                except PermissionError:
                    print(f"  ❌ Cannot read base path")
                    self.issues.append(f"No read permission: {config.base_path}")
                    all_ok = False

            # Check local path writable
            if config.local_path.exists():
                test_file = config.local_path / ".health_check_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    print(f"  ✅ Can write to local path")
                except PermissionError:
                    print(f"  ❌ Cannot write to local path")
                    self.issues.append(f"No write permission: {config.local_path}")
                    all_ok = False

            return all_ok
        except Exception as e:
            self.warnings.append(f"Permission check skipped: {e}")
            return True

    def check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            config = Config(self.config_path)

            if config.local_path.exists():
                import shutil
                total, used, free = shutil.disk_usage(config.local_path)

                free_gb = free // (2**30)
                total_gb = total // (2**30)
                percent_free = (free / total) * 100

                print(f"  Disk space: {free_gb}GB free of {total_gb}GB ({percent_free:.1f}%)")

                if free_gb < 1:
                    self.issues.append(f"Very low disk space: {free_gb}GB free")
                    return False
                elif free_gb < 5:
                    self.warnings.append(f"Low disk space: {free_gb}GB free")

                print(f"  ✅ Sufficient disk space")

            return True
        except Exception as e:
            self.warnings.append(f"Disk space check skipped: {e}")
            return True


def main():
    """Run health check."""
    import argparse

    parser = argparse.ArgumentParser(description="MP3 Service Health Check")
    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Path to configuration file'
    )
    args = parser.parse_args()

    checker = HealthCheck(args.config)
    success = checker.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
