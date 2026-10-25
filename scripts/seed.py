"""Forwarder to scripts/seed_demo.py with proper sys.path resolution."""
import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_demo import seed_demo_environment

if __name__ == "__main__":
    seed_demo_environment()
