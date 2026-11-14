"""Punto de entrada de PyInstaller para el companion."""

import multiprocessing
import sys

from askforever.cli import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
