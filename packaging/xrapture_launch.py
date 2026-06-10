"""PyInstaller entry script.

Imports the package (so the relative imports in ``xrapture.__main__`` resolve) and
hands off to its ``main()``, which dispatches to the menu-bar app or, when invoked
with ``--role``, to a child UI process.
"""

from xrapture.__main__ import main

if __name__ == "__main__":
    main()
