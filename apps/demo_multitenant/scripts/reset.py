"""Reset the multitenant demo's runtime data back to the committed seed.

Deletes `apps/demo_multitenant/.data` (the directory the management API reads and writes
communities from while the demo is running) and recreates it from `apps/demo_multitenant/seed`.
"""

import shutil
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DATA_DIR = Path(__file__).resolve().parent.parent / ".data"


def main() -> None:
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    shutil.copytree(SEED_DIR, DATA_DIR)
    print(f"Reset {DATA_DIR} from {SEED_DIR}")


if __name__ == "__main__":
    main()
