import sys
from pathlib import Path

DEVKIT_DIR = Path(__file__).resolve().parents[1]
if str(DEVKIT_DIR) not in sys.path:
    sys.path.insert(0, str(DEVKIT_DIR))
