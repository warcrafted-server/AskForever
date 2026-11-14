"""Permite ejecutar el companion con `python -m askforever`."""

import multiprocessing
import sys

from .cli import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
