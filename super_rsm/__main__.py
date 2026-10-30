"""
super_rsm/__main__.py

Entrypoint allowing `python -m super_rsm` to launch the SuperRSM desktop GUI.
"""

import sys
from super_rsm.gui.app import main

if __name__ == "__main__":
    sys.exit(main())

