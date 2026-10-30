"""
rsm_gui.py

Clean root entrypoint launching the modularized SuperRSM desktop GUI.
"""

import sys
from super_rsm.gui import RSMApp, RSMGui, main

__all__ = ["RSMApp", "RSMGui", "main"]

if __name__ == "__main__":
    sys.exit(main())
