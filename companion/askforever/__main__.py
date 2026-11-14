"""Permite ejecutar el companion con `python -m askforever`."""

import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
