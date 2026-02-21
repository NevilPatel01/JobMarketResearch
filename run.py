#!/usr/bin/env python3
"""
Runner script for Canada Tech Job Compass CLI.
This properly sets up the Python path and imports.
"""

import sys
from pathlib import Path

# Add src directory to Python path
repo_root = Path(__file__).resolve().parent
src_path = repo_root / "src"
sys.path.insert(0, str(src_path))

# Now import and run the main CLI
if __name__ == '__main__':
    from main import cli
    cli()
