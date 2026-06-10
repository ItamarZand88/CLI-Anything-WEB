import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for pkg_dir in (ROOT / "devkit", ROOT / "cli-web-core"):
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))
