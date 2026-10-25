"""Forwarder to eval/run_all_evals.py with proper sys.path resolution."""
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.run_all_evals import main

if __name__ == "__main__":
    main()
