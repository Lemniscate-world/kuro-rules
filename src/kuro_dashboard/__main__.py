"""python -m kuro_dashboard — sert l API + dashboard (defaut port 8767)."""

import sys

from .api import main

if __name__ == "__main__":
    sys.exit(main())
