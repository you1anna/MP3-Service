#!/usr/bin/env python3
"""
Setup wizard for MP3 Service
Interactive configuration and dependency checking
"""

import sys
import subprocess
from pathlib import Path
import json


def print_banner():
    """Print setup banner."""
    print("=" * 70)
    print("  MP3 Service Setup Wizard")
    print("=" * 70)
    print()


def check_python_version():
    """Check if Python version is adequate."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")

    required = {
        'mutagen': 'Audio tag manipulation',
        'watchdog': 'File system watching (optional)',
    }

    optional = {
        'librosa': 'BPM detection',
        'numpy': 'Required by librosa',
        'soundfile': 'Audio file I/O',
    }

    missing_required = []
    missing_optional = []

    for package, description in required.items():
        try:
            __import__(package)
            print(f"  ✅ {package} - {description}")
        except ImportError:
            print(f"  ❌ {package} - {description}")
            missing_required.append(package)

    for package, description in optional.items():
        try:
            __import__(package)
            print(f"  ✅ {package} - {description}")
        except ImportError:
            print(f"  ⚠️  {package} - {description} (optional)")
            missing_optional.append(package)

    return missing_required, missing_optional


def install_dependencies(missing):
    """Offer to install missing dependencies."""
    if not missing:
        return True

    print(f"\n📦 Missing required packages: {', '.join(missing)}")
    response = input("Install now? (y/n): ").lower().strip()

    if response == 'y':
        print("\n Installing dependencies...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("   Try manually: pip install -r requirements.txt")
            return False
    return False


def create_config_interactive():
    """Create configuration interactively."""
    print("\n⚙️  Configuration Setup")
    print("-" * 70)

    config = {}

    # Base path
    print("\n📁 Where should the service monitor for incoming audio files?")
    default_base = str(Path.home() / "Music" / "Incoming")
    base_path = input(f"   Base path [{default_base}]: ").strip()
    config['base_path'] = base_path if base_path else default_base

    # Local path
    print("\n📁 Where should processed files be saved?")
    default_local = str(Path.home() / "Music" / "Processed")
    local_path = input(f"   Local path [{default_local}]: ").strip()
    config['local_path'] = local_path if local_path else default_local

    # Network share
    print("\n🌐 Do you want to copy files to a network share?")
    use_network = input("   Enable network sharing? (y/n) [n]: ").lower().strip()
    config['include_share'] = use_network == 'y'

    if config['include_share']:
        network_path = input("   Network path (e.g., //server/share): ").strip()
        config['network_path'] = network_path
    else:
        config['network_path'] = ""

    config['desktop_path'] = ""

    # Poll interval
    print("\n⏱️  How often should the service check for new files?")
    poll = input("   Poll interval in seconds [40]: ").strip()
    try:
        config['poll_interval'] = int(poll) if poll else 40
    except ValueError:
        config['poll_interval'] = 40

    # File formats
    config['supported_extensions'] = [
        ".mp3", ".m4a", ".wav", ".aif", ".aiff", ".flac"
    ]

    # BPM range
    config['bpm_range'] = {"min": 65, "max": 135}

    # Logging
    config['log_file'] = "mp3_service.log"

    print("\n📊 Choose logging level:")
    print("   1. DEBUG (detailed, for troubleshooting)")
    print("   2. INFO (normal operation)")
    print("   3. WARNING (only warnings and errors)")
    level_choice = input("   Choice [2]: ").strip()

    levels = {
        '1': 'DEBUG',
        '2': 'INFO',
        '3': 'WARNING'
    }
    config['log_level'] = levels.get(level_choice, 'INFO')

    return config


def create_directories(config):
    """Create necessary directories."""
    print("\n📁 Creating directories...")

    paths_to_create = [
        ('base_path', 'Incoming files'),
        ('local_path', 'Processed files'),
    ]

    for key, description in paths_to_create:
        path = Path(config.get(key, ''))
        if path and not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ Created {description}: {path}")
            except Exception as e:
                print(f"  ⚠️  Could not create {path}: {e}")
        elif path.exists():
            print(f"  ✅ {description} exists: {path}")


def run_validation():
    """Run validation command."""
    print("\n🔍 Validating configuration...")
    try:
        subprocess.check_call([sys.executable, 'main.py', 'validate'])
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Validation found some issues (see above)")
        return False


def main():
    """Main setup wizard."""
    print_banner()

    # Check Python version
    if not check_python_version():
        print("\n❌ Setup cannot continue. Please upgrade Python.")
        sys.exit(1)

    # Check dependencies
    missing_required, missing_optional = check_dependencies()

    if missing_required:
        if not install_dependencies(missing_required):
            print("\n❌ Required dependencies not installed.")
            print("   Please install manually and run setup again.")
            sys.exit(1)

    if missing_optional:
        print(f"\n⚠️  Optional packages not installed: {', '.join(missing_optional)}")
        print("   BPM detection will be disabled without librosa.")
        response = input("   Install optional packages? (y/n): ").lower().strip()
        if response == 'y':
            install_dependencies(missing_optional)

    # Check if config exists
    config_file = Path('config.json')
    if config_file.exists():
        print("\n⚠️  config.json already exists")
        response = input("   Overwrite? (y/n): ").lower().strip()
        if response != 'y':
            print("\n✅ Setup cancelled. Existing configuration preserved.")
            return

    # Create configuration
    config = create_config_interactive()

    # Save configuration
    print("\n💾 Saving configuration...")
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print("  ✅ Configuration saved to config.json")

    # Create directories
    create_directories(config)

    # Run validation
    run_validation()

    # Final instructions
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Review config.json and adjust if needed")
    print("  2. Test with: python main.py start --dry-run")
    print("  3. Run service: python main.py start --watch")
    print("\nFor more information:")
    print("  - Run: python main.py --help")
    print("  - See: README.md")
    if sys.platform == 'win32':
        print("  - Windows guide: WINDOWS.md")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        sys.exit(1)
