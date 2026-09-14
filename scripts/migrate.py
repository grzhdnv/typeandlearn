"""Migration CLI wrapper to run the database migration helper."""

import sys
from pathlib import Path

# Add apps/backend to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent / "apps" / "backend"
sys.path.append(str(backend_dir))

from core.migration import migrate_data

if __name__ == "__main__":
    migrate_data()
