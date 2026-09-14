"""Top-level entry point.

PyInstaller (and `python main.py` in general) treats the file it's given as a
standalone script with no parent package, which breaks the `from . import ...`
relative imports used inside nebula_launcher/. Running through this wrapper
instead makes `nebula_launcher` get imported as a real package, so relative
imports work both in development and in the frozen .exe/.app/binary.
"""
from nebula_launcher.main import main

if __name__ == "__main__":
    main()
