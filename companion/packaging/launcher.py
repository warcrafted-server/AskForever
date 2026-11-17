"""Punto de entrada de PyInstaller para el companion."""

import multiprocessing
import os
import sys

from askforever.cli import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    sys.exit(main())
